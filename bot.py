import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Читаем ключи из переменных окружения
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здравствуйте! Я помощник фотографа. Чем могу помочь?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_lower = user_text.lower()
    
    # 1. Железный ответ на цену
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

    # 2. Ответ через Gemini
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        payload = {
            "contents": [{"parts": [{"text": user_text}]}]
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            await update.message.reply_text(ai_text)
        else:
            await update.message.reply_text("Напишите нашему менеджеру: @dmitryprof")
    except:
        await update.message.reply_text("Напишите нашему менеджеру: @dmitryprof")

if __name__ == '__main__':
    if not TOKEN:
        print("Ошибка: Нет токена Telegram!")
    else:
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        print("Бот запускается...")
        app.run_polling()
