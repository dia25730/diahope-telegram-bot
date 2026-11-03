# Diahope Christ Foundation Telegram Bot and Mini App

English/Amharic Telegram bot with a Flask webhook and a Telegram Mini App prayer-request form. The bot's existing commands, including /start, are preserved.

## Render deployment

- Service type: Web Service
- Build command: pip install -r requirements.txt
- Start command:
  python -c 'from bot import configure_webhook; configure_webhook()' && exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 30 bot:app

The start command configures the Telegram webhook without discarding queued updates, then runs the Flask app under Gunicorn. Keep one worker because the current per-user rate limiter is held in process memory.

Set these environment variables in Render's secret/environment settings (never commit their values):

- TELEGRAM_BOT_TOKEN — the existing bot token.
- WEBHOOK_SECRET — a random 1–256 character value using ASCII letters, numbers, underscore, or hyphen.
- ADMIN_CHAT_ID — the private chat or group that should receive prayer requests. The bot must be able to message that destination; an individual admin should start the bot first.
- DIAHOPE_WEBSITE_URL — optional HTTPS website URL shown by the existing /start website button.
- MINI_APP_URL — optional full HTTPS Mini App URL, including /app. When omitted, the app link is derived from Render's RENDER_EXTERNAL_URL.

Render supplies PORT and RENDER_EXTERNAL_URL. After deployment, send /start to the bot in a private chat to open the Mini App. The page is served at /app; prayer requests are sent privately to ADMIN_CHAT_ID and are not stored by this app. Telegram initData is HMAC-validated server-side, limited to one hour old (with a small clock-skew allowance), and requests are rate-limited per Telegram user in the running process.

If you want an additional persistent menu entry, configure the bot's Mini App/menu button in BotFather. The /start launch button is supplied by the bot code.

## Local checks

Run the built-in tests with:

python -m unittest discover -v

The bot requires TELEGRAM_BOT_TOKEN and WEBHOOK_SECRET before its Flask app can be imported. Keep secrets in Render's environment settings or a local secret manager, not in source control.
