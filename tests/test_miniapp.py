import hashlib
import hmac
import importlib
import json
import os
import sys
import time
import unittest
from urllib.parse import urlencode
from unittest.mock import patch

from flask import Flask

import miniapp

TEST_TOKEN = "unit-test-token"
TEST_USER = {"id": 424242, "first_name": "Test", "username": "test_user"}


def make_init_data(user=None, auth_date=None, token=TEST_TOKEN):
    params = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "query_id": "test-query",
        "user": json.dumps(TEST_USER if user is None else user, separators=(",", ":")),
    }
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


class InitDataTests(unittest.TestCase):
    def test_valid_init_data_returns_verified_user(self):
        self.assertEqual(miniapp.validate_init_data(make_init_data(), TEST_TOKEN), TEST_USER)

    def test_tampered_data_is_rejected(self):
        payload = make_init_data().replace("test-query", "forged-query")
        self.assertIsNone(miniapp.validate_init_data(payload, TEST_TOKEN))

    def test_duplicate_fields_are_rejected(self):
        payload = make_init_data() + "&auth_date=1"
        self.assertIsNone(miniapp.validate_init_data(payload, TEST_TOKEN))

    def test_stale_and_future_auth_dates_are_rejected(self):
        old = make_init_data(auth_date=int(time.time()) - miniapp.INITDATA_MAX_AGE - 1)
        future = make_init_data(auth_date=int(time.time()) + miniapp.INITDATA_FUTURE_SKEW + 2)
        self.assertIsNone(miniapp.validate_init_data(old, TEST_TOKEN))
        self.assertIsNone(miniapp.validate_init_data(future, TEST_TOKEN))

    def test_user_without_numeric_id_is_rejected(self):
        self.assertIsNone(miniapp.validate_init_data(make_init_data(user={"first_name": "No ID"}), TEST_TOKEN))


class PrayerRouteTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": TEST_TOKEN,
            "ADMIN_CHAT_ID": "test-admin-chat",
        })
        self.env.start()
        miniapp._recent.clear()
        self.app = Flask(__name__)
        self.app.config["MAX_CONTENT_LENGTH"] = 1_000_000
        self.app.register_blueprint(miniapp.miniapp_bp)
        self.client = self.app.test_client()

    def tearDown(self):
        miniapp._recent.clear()
        self.env.stop()

    def post_request(self, **overrides):
        payload = {
            "initData": make_init_data(),
            "request": "Please pray for my family.",
            "name": "<family>",
            "anonymous": False,
            "consent": True,
        }
        payload.update(overrides)
        return self.client.post("/api/prayer", json=payload)

    def test_valid_request_is_sent_to_admin_and_escaped(self):
        with patch("miniapp.requests.post") as send:
            send.return_value.ok = True
            response = self.post_request()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ok"])
        outgoing = send.call_args.kwargs["json"]
        self.assertEqual(outgoing["chat_id"], "test-admin-chat")
        self.assertIn("&lt;family&gt;", outgoing["text"])
        self.assertNotIn("<family>", outgoing["text"])

    def test_invalid_telegram_auth_is_rejected(self):
        with patch("miniapp.requests.post") as send:
            response = self.post_request(initData="bad-data")
        self.assertEqual(response.status_code, 401)
        send.assert_not_called()

    def test_honeypot_does_not_send_a_message(self):
        with patch("miniapp.requests.post") as send:
            response = self.post_request(website="bot-filled-this")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ok"])
        send.assert_not_called()

    def test_user_rate_limit_is_enforced(self):
        with patch("miniapp.requests.post") as send:
            send.return_value.ok = True
            statuses = [self.post_request().status_code for _ in range(miniapp.RATE_LIMIT + 1)]
        self.assertEqual(statuses, [200] * miniapp.RATE_LIMIT + [429])


class BotIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": TEST_TOKEN,
            "WEBHOOK_SECRET": "test-webhook-secret",
            "RENDER_EXTERNAL_URL": "https://diahope-test.onrender.com",
            "DIAHOPE_WEBSITE_URL": "https://diahope.example.org",
            "MINI_APP_URL": "",
            "PORT": "10000",
        })
        self.env.start()
        sys.modules.pop("bot", None)
        self.bot = importlib.import_module("bot")
        self.client = self.bot.app.test_client()

    def tearDown(self):
        sys.modules.pop("bot", None)
        self.env.stop()

    def test_app_serves_the_mini_app_and_health_route(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.get("/app")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="prayerForm"', response.data)
        response.close()

    def test_start_keeps_welcome_and_adds_mini_app_button(self):
        with patch.object(self.bot.requests, "post") as send:
            send.return_value.raise_for_status.return_value = None
            response = self.client.post(
                "/telegram",
                headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
                json={"message": {"chat": {"id": 101}, "text": "/start"}},
            )
        self.assertEqual(response.status_code, 200)
        payload = send.call_args.kwargs["json"]
        self.assertIn("Welcome to Diahope", payload["text"])
        buttons = payload["reply_markup"]["inline_keyboard"]
        self.assertEqual(buttons[0][0]["web_app"]["url"], "https://diahope-test.onrender.com/app")
        self.assertTrue(any("url" in row[0] for row in buttons))

    def test_wrong_webhook_secret_is_rejected(self):
        response = self.client.post(
            "/telegram",
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            json={"message": {"chat": {"id": 101}, "text": "/start"}},
        )
        self.assertEqual(response.status_code, 401)

    def test_configuring_webhook_does_not_drop_pending_updates(self):
        with patch.object(self.bot.requests, "post") as send:
            send.return_value.raise_for_status.return_value = None
            self.bot.configure_webhook()
        webhook_payload = send.call_args.kwargs["json"]
        self.assertEqual(webhook_payload["url"], "https://diahope-test.onrender.com/telegram")
        self.assertNotIn("drop_pending_updates", webhook_payload)


if __name__ == "__main__":
    unittest.main()
