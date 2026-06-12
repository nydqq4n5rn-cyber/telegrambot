import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем переменные окружения
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
PORT = int(os.environ.get("PORT", 8080))
# ВАЖНО: укажи сюда свой URL из Render (например, https://tvoj-bot.onrender.com)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здравствуйте! Я помощник фотографа. Чем могу помочь?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_lower = user_text.lower()
    
    # 1. Железный ответ на цену (без запроса к ИИ)
    if any(w in user_lower for w in ["цена", "прайс", "сколько стоит", "индивидуальная", "свадебная"]):
        msg = (
            "Добрый день!\n"
            "• Индивидуальная фотосессия: 6500 руб./час.\n"
            "• Свадебная съёмка: 55 000 руб. за 12 часов.\n"
            "Условия: студия оплачивается отдельно, фото отдаем до 7 дней."
        )
        await update.message.reply_text(msg)
        return

    # 2. Ответ через Gemini
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": user_text}]}]}
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            await update.message.reply_text(ai_text)
        else:
            await update.message.reply_text("Извините, сейчас технические работы. Напишите @dmitryprof")
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        await update.message.reply_text("Напишите нашему менеджеру: @dmitryprof")

if __name__ == '__main__':
    if not TOKEN or not GEMINI_KEY or not WEBHOOK_URL:
        print("Ошибка: Проверьте TELEGRAM_TOKEN, GEMINI_KEY и WEBHOOK_URL в настройках Render!")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск через Webhook (единственный способ для Render Web Service)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )
