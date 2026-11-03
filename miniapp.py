"""
Diahope Mini App add-on for the existing Flask webhook service.

Adds:
    GET  /app          -> Serves diahope_miniapp.html
    POST /api/prayer   -> Receives prayer requests and forwards them
                          privately to your admin Telegram chat.

Environment variables:
    Existing bot token variable:
    BOT_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_TOKEN,
    BOT_API_TOKEN, or TOKEN.

    ADMIN_CHAT_ID:
    The Telegram chat ID that receives prayer requests.
"""

import hashlib
import hmac
import html
import json
import os
import time
from urllib.parse import parse_qsl

import requests

from flask import (
    Blueprint,
    jsonify,
    make_response,
    request,
    send_from_directory,
)


miniapp_bp = Blueprint("miniapp", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PAGE = "diahope_miniapp.html"

MAX_BODY_BYTES = 20000
MAX_REQUEST_LEN = 1000
MAX_NAME_LEN = 60

MAX_INIT_DATA_LENGTH = 16_384
INITDATA_MAX_AGE = 60 * 60
INITDATA_FUTURE_SKEW = 60

RATE_LIMIT = 3
RATE_WINDOW = 60 * 60

_recent = {}

TOKEN_NAMES = (
    "BOT_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_TOKEN",
    "BOT_API_TOKEN",
    "TOKEN",
)


def _bot_token():
    for name in TOKEN_NAMES:
        value = os.environ.get(name)
        if value:
            return value

    return ""


def validate_init_data(init_data: str, token: str):
    """Verify Telegram Mini App initData and reject stale or ambiguous payloads."""

    if (
        not isinstance(init_data, str)
        or not init_data
        or len(init_data) > MAX_INIT_DATA_LENGTH
        or not token
    ):
        return None

    try:
        parsed = parse_qsl(
            init_data,
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=50,
        )
        pairs = {}
        for key, value in parsed:
            if key in pairs:
                return None
            pairs[key] = value

        received_hash = pairs.pop("hash", None)
        if (
            not received_hash
            or len(received_hash) != 64
            or any(char not in "0123456789abcdef" for char in received_hash)
        ):
            return None

        check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(pairs.items())
        )

        secret = hmac.new(
            b"WebAppData",
            token.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected = hmac.new(
            secret,
            check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, received_hash):
            return None

        auth_date = int(pairs.get("auth_date", ""))
        now = time.time()
        if (
            auth_date <= 0
            or auth_date > now + INITDATA_FUTURE_SKEW
            or now - auth_date > INITDATA_MAX_AGE
        ):
            return None

        user = json.loads(pairs.get("user", "{}"))
        if (
            not isinstance(user, dict)
            or not isinstance(user.get("id"), int)
            or isinstance(user.get("id"), bool)
            or user["id"] <= 0
        ):
            return None

        return user
    except (TypeError, ValueError, UnicodeError):
        return None


def _rate_limited(user_id) -> bool:
    now = time.time()

    if len(_recent) > 1000:
        for uid in [
            u for u, timestamps in _recent.items()
            if not timestamps
            or now - timestamps[-1] >= RATE_WINDOW
        ]:
            _recent.pop(uid, None)

    hits = [
        timestamp
        for timestamp in _recent.get(user_id, [])
        if now - timestamp < RATE_WINDOW
    ]

    if len(hits) >= RATE_LIMIT:
        _recent[user_id] = hits
        return True

    hits.append(now)
    _recent[user_id] = hits

    return False


@miniapp_bp.after_request
def _headers(resp):
    if (
        request.path == "/app"
        or request.path.startswith("/api/prayer")
    ):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Cache-Control"] = "no-store"

    return resp


@miniapp_bp.app_errorhandler(413)
def _payload_too_large(error):
    if request.path == "/api/prayer":
        return jsonify(ok=False, error="too_large"), 413
    return error


@miniapp_bp.route("/app")
def serve_app():
    resp = make_response(
        send_from_directory(BASE_DIR, PAGE)
    )

    resp.headers["Content-Type"] = "text/html; charset=utf-8"

    return resp


@miniapp_bp.route("/api/prayer", methods=["POST"])
def prayer():
    raw_body = request.get_data(cache=True)
    if len(raw_body) > MAX_BODY_BYTES:
        return jsonify(ok=False, error="too_large"), 413

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(ok=False, error="invalid"), 400

    # Honeypot: real users never fill this hidden field.
    if data.get("website"):
        return jsonify(ok=True)

    token = _bot_token()
    if not token:
        print("Mini App: bot token is not configured", flush=True)
        return jsonify(ok=False, error="not_configured"), 503

    user = validate_init_data(data.get("initData", ""), token)
    if not user:
        return jsonify(ok=False, error="unauthorized"), 401

    admin_chat = os.environ.get("ADMIN_CHAT_ID", "").strip()
    if not admin_chat:
        print("Mini App: admin destination is not configured", flush=True)
        return jsonify(ok=False, error="not_configured"), 503

    raw_text = data.get("request")
    raw_name = data.get("name", "")
    anonymous = data.get("anonymous", False)
    if (
        not isinstance(raw_text, str)
        or not isinstance(raw_name, str)
        or not isinstance(anonymous, bool)
        or data.get("consent") is not True
    ):
        return jsonify(ok=False, error="invalid"), 400

    text = raw_text.strip()
    name = raw_name.strip()[:MAX_NAME_LEN]
    if len(text) < 5 or len(text) > MAX_REQUEST_LEN:
        return jsonify(ok=False, error="invalid"), 400

    if _rate_limited(user["id"]):
        return jsonify(ok=False, error="rate_limited"), 429

    if anonymous:
        who = "Anonymous"
    else:
        username = user.get("username")
        handle = f" (@{username})" if isinstance(username, str) and username else ""
        first_name = user.get("first_name")
        first_name = first_name if isinstance(first_name, str) and first_name else "Friend"
        who = (name or first_name) + handle

    message = (
        "\U0001F64F <b>New prayer request</b>\n"
        f"<b>From:</b> {html.escape(who)}\n\n"
        f"{html.escape(text)}"
    )

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": admin_chat,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )

        if not response.ok:
            print(
                f"Mini App: prayer delivery failed (HTTP {response.status_code})",
                flush=True,
            )
            return jsonify(ok=False, error="send_failed"), 502

    except requests.RequestException:
        print("Mini App: prayer delivery failed (network error)", flush=True)
        return jsonify(ok=False, error="send_failed"), 502

    # Nothing is stored on the server.
    return jsonify(ok=True)
