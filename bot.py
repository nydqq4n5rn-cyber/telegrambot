import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем данные из переменных Render
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
PORT = int(os.environ.get("PORT", 8080))
# Твой URL на Render
WEBHOOK_URL = "https://telegrambot-4-sib5.onrender.com"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здравствуйте! Я помощник фотографа. Чем могу помочь?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_lower = user_text.lower()
    
    # Прайс-лист
    if any(w in user_lower for w in ["цена", "прайс", "сколько стоит", "съёмка", "свадебная", "индивидуальная"]):
        msg = (
            "Добрый день!\n"
            "• Индивидуальная фотосессия: 6500 руб./час.\n"
            "• Свадебная съёмка: 55 000 руб. за 12 часов.\n"
            "Важно:\n"
            "– Студия оплачивается отдельно.\n"
            "– Срок отдачи фотографий – до 7 дней.\n\n"
            "Подскажите, какая именно съёмка вас интересует?"
        )
        await update.message.reply_text(msg)
        return

    # Ответ через Gemini
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": user_text}]}]}
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            await update.message.reply_text(ai_text)
        else:
            await update.message.reply_text("Напишите нашему менеджеру: @dmitryprof")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Напишите нашему менеджеру: @dmitryprof")

if __name__ == '__main__':
    if not TOKEN or not GEMINI_KEY:
        print("Ошибка: Отсутствуют токены в переменных окружения!")
        exit(1)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск через вебхук
    print("Запуск бота через Webhook...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )
