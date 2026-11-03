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

INITDATA_MAX_AGE = 24 * 60 * 60

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
    """Verify Telegram Mini App initData."""

    if not init_data or not token:
        return None

    try:
        pairs = dict(
            parse_qsl(init_data, keep_blank_values=True)
        )

        received_hash = pairs.pop("hash", None)

        if not received_hash:
            return None

        check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(pairs.items())
        )

        secret = hmac.new(
            b"WebAppData",
            token.encode(),
            hashlib.sha256,
        ).digest()

        expected = hmac.new(
            secret,
            check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, received_hash):
            return None

        if time.time() - int(
            pairs.get("auth_date", "0")
        ) > INITDATA_MAX_AGE:
            return None

        return json.loads(
            pairs.get("user", "{}")
        ) or None

    except Exception:
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
        resp.headers["Cache-Control"] = "no-cache"

    return resp


@miniapp_bp.route("/app")
def serve_app():
    resp = make_response(
        send_from_directory(BASE_DIR, PAGE)
    )

    resp.headers["Content-Type"] = "text/html; charset=utf-8"

    return resp


@miniapp_bp.route("/api/prayer", methods=["POST"])
def prayer():

    if (
        request.content_length
        and request.content_length > MAX_BODY_BYTES
    ):
        return jsonify(ok=False, error="too_large"), 413

    data = request.get_json(silent=True) or {}

    # Honeypot: real users never fill this hidden field.
    if data.get("website"):
        return jsonify(ok=True)

    token = _bot_token()
    admin_chat = os.environ.get("ADMIN_CHAT_ID", "").strip()

    if not token or not admin_chat:
        print(
            "Mini App: bot token variable or ADMIN_CHAT_ID is missing",
            flush=True,
        )
        return jsonify(ok=False, error="not_configured"), 503

    user = validate_init_data(
        str(data.get("initData", "")),
        token,
    )

    if not user:
        return jsonify(ok=False, error="unauthorized"), 401

    text = str(data.get("request", "")).strip()
    name = str(data.get("name", "")).strip()[:MAX_NAME_LEN]
    anonymous = bool(data.get("anonymous"))

    if (
        len(text) < 5
        or len(text) > MAX_REQUEST_LEN
        or data.get("consent") is not True
    ):
        return jsonify(ok=False, error="invalid"), 400

    if _rate_limited(user.get("id")):
        return jsonify(ok=False, error="rate_limited"), 429

    if anonymous:
        who = "Anonymous"
    else:
        handle = (
            f" (@{user['username']})"
            if user.get("username")
            else ""
        )

        who = (
            name
            or user.get("first_name", "Friend")
        ) + handle

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
            try:
                reason = response.json().get(
                    "description", ""
                )
            except Exception:
                reason = ""

            print(
                f"Mini App: prayer delivery failed "
                f"({response.status_code}) {reason}",
                flush=True,
            )

            return jsonify(
                ok=False,
                error="send_failed",
            ), 502

    except requests.RequestException:
        print(
            "Mini App: prayer delivery failed (network error)",
            flush=True,
        )

        return jsonify(
            ok=False,
            error="send_failed",
        ), 502

    # Nothing is stored on the server.
    return jsonify(ok=True)
