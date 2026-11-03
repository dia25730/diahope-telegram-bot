import os
import logging
import requests
from flask import Flask, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBSITE_URL = os.environ.get("DIAHOPE_WEBSITE_URL", "https://example.com")
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]
PORT = int(os.environ.get("PORT", "10000"))
API = f"https://api.telegram.org/bot{TOKEN}"

WELCOME = (
    "💜 Welcome to Diahope Christ Foundation!\n\n"
    "We believe every child deserves love, dignity, inclusion, and hope. "
    "Explore our mission, learn about disabilities, volunteer, or share a prayer request.\n\n"
    "እንኳን ወደ ዳያሆፕ ክርስቲያን ፋውንዴሽን በደህና መጡ!\n"
    "እያንዳንዱ ሕፃን ፍቅር፣ ክብር፣ አካታችነትና ተስፋ ይገባዋል።"
)

REPLIES = {
    "/about": (
        "💜 Diahope Christ Foundation\n"
        "Supporting children with disabilities through love, inclusion, awareness, and hope.\n\n"
        "የአካል ጉዳት ላላቸው ሕፃናት በፍቅር፣ በአካታችነት፣ በግንዛቤና በተስፋ የሚደግፍ ድርጅት።\n\n"
        "Different Abilities. Equal Dignity. Unlimited Hope.\n"
        "የተለያዩ ችሎታዎች። እኩል ክብር። ወሰን የሌለው ተስፋ።"
    ),
    "/disabilities": (
        "Disability awareness 💜\n"
        "Children may have physical, sensory, intellectual, developmental, or learning disabilities. "
        "Every child is unique. Use respectful language, include children, and ask what support they prefer.\n\n"
        "የአካል ጉዳት ግንዛቤ 💜\n"
        "ልጆች የአካል፣ የስሜት ሕዋሳት፣ የአእምሮ ወይም የእድገት እና የመማር ችግሮች ሊኖራቸው ይችላል። "
        "እያንዳንዱ ልጅ ልዩ ነው፤ በክብር እንነጋገር፣ እና አካታች እንሁን።"
    ),
    "/children": (
        "💜 Diahope stands for children with disabilities and their families. "
        "We aim to promote dignity, inclusion, awareness, and access to supportive resources.\n\n"
        "ዳያሆፕ የአካል ጉዳት ላላቸው ሕፃናትና ለቤተሰቦቻቸው ይቆማል። "
        "ክብርን፣ አካታችነትን፣ ግንዛቤንና ድጋፍን ለማበረታታት እንሰራለን።"
    ),
    "/donate": (
        "Thank you for wanting to support Diahope! 💜 Donation methods are being prepared. "
        "Please contact the foundation for verified details.\n\n"
        "ዳያሆፕን ለመደገፍ ስለፈለጉ እናመሰግናለን! የልገሳ መንገዶች በዝግጅት ላይ ናቸው።"
    ),
    "/volunteer": (
        "Thank you for your interest in volunteering with Diahope! 💜 "
        "Please send us your name, skills, and how you'd like to help.\n\n"
        "ዳያሆፕን በበጎ ፈቃድ ለመደገፍ ስለፈለጉ እናመሰግናለን! "
        "ስምዎን፣ ችሎታዎንና ሊረዱበት የሚፈልጉትን መንገድ ይላኩልን።"
    ),
    "/prayer": (
        "🙏 You may send your prayer request in a message. Please avoid sharing sensitive personal details.\n\n"
        "🙏 የጸሎት ጥያቄዎን በመልዕክት መላክ ይችላሉ። የግል ሚስጥራዊ መረጃዎችን ከመጋራት ይቆጠቡ።"
    ),
    "/contact": (
        "💜 Contact Diahope Christ Foundation\n"
        "Our official contact details are being prepared. Please visit our website for updates.\n\n"
        "የዳያሆፕ ክርስቲያን ፋውንዴሽን የእውቂያ መረጃ በዝግጅት ላይ ነው።"
    ),
    "/help": (
        "💜 Diahope Bot Commands\n"
        "/start — Welcome | መጀመሪያ\n"
        "/about — About Diahope | ስለ ዳያሆፕ\n"
        "/disabilities — Disability awareness | ግንዛቤ\n"
        "/children — Our mission for children | ስለ ሕፃናት\n"
        "/donate — Donation information | ልገሳ\n"
        "/volunteer — Volunteer | በጎ ፈቃድ\n"
        "/prayer — Prayer request | የጸሎት ጥያቄ\n"
        "/contact — Contact | እውቂያ\n"
        "/help — Help | እርዳታ"
    ),
}

def send_message(chat_id, text, include_website=False):
    payload = {"chat_id": chat_id, "text": text}
    if include_website:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": "Visit Diahope website 🌐", "url": WEBSITE_URL}]]
        }
    response = requests.post(f"{API}/sendMessage", json=payload, timeout=20)
    response.raise_for_status()

app = Flask(__name__)
from miniapp import miniapp_bp
app.register_blueprint(miniapp_bp)
@app.get("/")
def health():
    return "Diahope bot is running 💜", 200

@app.post("/telegram")
def telegram_webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token", "") != WEBHOOK_SECRET:
        return "Unauthorized", 401

    update = request.get_json(silent=True) or {}
    message = update.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return "OK", 200

    command = text.split()[0].split("@")[0].lower()
    if command == "/start":
        send_message(chat_id, WELCOME, include_website=True)
    elif command in REPLIES:
        send_message(chat_id, REPLIES[command])
    elif text.startswith("/"):
        send_message(chat_id, "I don't know that command yet. Please use /help. 💜")
    else:
        send_message(
            chat_id,
            "Thank you for messaging Diahope 💜 Please use /help to see what I can do.\n\n"
            "መልዕክትዎን ስለላኩ እናመሰግናለን። /help በመጠቀም የምሰራቸውን ይመልከቱ።"
        )
    return "OK", 200

if __name__ == "__main__":
    webhook_url = os.environ["RENDER_EXTERNAL_URL"].rstrip("/") + "/telegram"
    response = requests.post(
        f"{API}/setWebhook",
        json={"url": webhook_url, "secret_token": WEBHOOK_SECRET, "drop_pending_updates": True},
        timeout=20,
    )
    response.raise_for_status()
    logger.info("Telegram webhook configured.")
    app.run(host="0.0.0.0", port=PORT)
