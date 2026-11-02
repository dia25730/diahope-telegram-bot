import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Replace this with Diahope's published website URL before deploying.
WEBSITE_URL = os.environ.get("DIAHOPE_WEBSITE_URL", "https://example.com")

WELCOME = (
    "💜 Welcome to Diahope Christ Foundation!\n\n"
    "We believe every child deserves love, dignity, inclusion, and hope.\n"
    "Explore our mission, learn about disabilities, volunteer, or share a prayer request.\n\n"
    "እንኳን ወደ ዳያሆፕ ክርስቲያን ፋውንዴሽን በደህና መጡ!\n"
    "እያንዳንዱ ሕፃን ፍቅር፣ ክብር፣ አካታችነትና ተስፋ ይገባዋል።"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Visit Diahope website 🌐", url=WEBSITE_URL)]]
    await update.message.reply_text(WELCOME, reply_markup=InlineKeyboardMarkup(keyboard))

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 Diahope Christ Foundation\n"
        "Supporting children with disabilities through love, inclusion, awareness, and hope.\n\n"
        "የአካል ጉዳት ላላቸው ሕፃናት በፍቅር፣ በአካታችነት፣ በግንዛቤና በተስፋ የሚደግፍ ድርጅት።\n\n"
        "Different Abilities. Equal Dignity. Unlimited Hope.\n"
        "የተለያዩ ችሎታዎች። እኩል ክብር። ወሰን የሌለው ተስፋ።"
    )

async def disabilities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Disability awareness 💜\n"
        "Children may have physical, sensory, intellectual, developmental, or learning disabilities. "
        "Every child is unique. Use respectful language, include children, and ask what support they prefer.\n\n"
        "የአካል ጉዳት ግንዛቤ 💜\n"
        "ልጆች የአካል፣ የስሜት ሕዋሳት፣ የአእምሮ ወይም የእድገት እና የመማር ችግሮች ሊኖራቸው ይችላል። "
        "እያንዳንዱ ልጅ ልዩ ነው፤ በክብር እንነጋገር፣ እና አካታች እንሁን።"
    )

async def children(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 Diahope stands for children with disabilities and their families. "
        "We aim to promote dignity, inclusion, awareness, and access to supportive resources.\n\n"
        "ዳያሆፕ የአካል ጉዳት ላላቸው ሕፃናትና ለቤተሰቦቻቸው ይቆማል። "
        "ክብርን፣ አካታችነትን፣ ግንዛቤንና ድጋፍን ለማበረታታት እንሰራለን።"
    )

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Thank you for wanting to support Diahope! 💜\n"
        "Donation methods are being prepared. Please contact the foundation for verified details.\n\n"
        "ዳያሆፕን ለመደገፍ ስለፈለጉ እናመሰግናለን! የልገሳ መንገዶች በዝግጅት ላይ ናቸው።"
    )

async def volunteer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Thank you for your interest in volunteering with Diahope! 💜\n"
        "Please send us a message with your name, skills, and how you'd like to help.\n\n"
        "ዳያሆፕን በበጎ ፈቃድ ለመደገፍ ስለፈለጉ እናመሰግናለን! "
        "ስምዎን፣ ችሎታዎንና ሊረዱበት የሚፈልጉትን መንገድ ይላኩልን።"
    )

async def prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🙏 You may send your prayer request in a message. Please avoid sharing sensitive personal details.\n\n"
        "🙏 የጸሎት ጥያቄዎን በመልዕክት መላክ ይችላሉ። የግል ሚስጥራዊ መረጃዎችን ከመጋራት ይቆጠቡ።"
    )

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 Contact Diahope Christ Foundation\n"
        "Our official contact details are being prepared. Please visit our website for updates.\n\n"
        "የዳያሆፕ ክርስቲያን ፋውንዴሽን የእውቂያ መረጃ በዝግጅት ላይ ነው።"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
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
    )

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Thank you for messaging Diahope 💜 Please use /help to see what I can do.\n\n"
        "መልዕክትዎን ስለላኩ እናመሰግናለን። /help በመጠቀም የምሰራቸውን ይመልከቱ።"
    )

def main():
    if not TOKEN:
        raise RuntimeError("Please set the TELEGRAM_BOT_TOKEN environment variable.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("disabilities", disabilities))
    app.add_handler(CommandHandler("children", children))
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(CommandHandler("volunteer", volunteer))
    app.add_handler(CommandHandler("prayer", prayer))
    app.add_handler(CommandHandler("contact", contact))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    app.run_polling()

if __name__ == "__main__":
    main()
