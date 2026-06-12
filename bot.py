import os
import requests
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# 1. Настройка Flask для «обмана» Render
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 2. Настройка бота
logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здравствуйте! Я помощник фотографа. Чем могу помочь?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_lower = user_text.lower()
    
    # ПРАЙС-ЛИСТ (встроен в бота)
    if any(w in user_lower for w in ["цена", "прайс", "сколько стоит", "съёмка", "индивидуальная", "свадебная"]):
        msg = (
            "Добрый день!\n"
            "• Индивидуальная фотосессия: 6500 руб./час.\n"
            "• Свадебная съёмка: 55 000 руб. за 12 часов.\n"
            "Важные условия:\n"
            "– Студия оплачивается клиентом отдельно.\n"
            "– Срок отдачи фотографий – до 7 дней.\n\n"
            "Подскажите, какая именно съёмка вас интересует?"
        )
        await update.message.reply_text(msg)
        return

    # Запрос к ИИ, если это не вопрос о цене
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        resp = requests.post(url, json={"contents": [{"parts": [{"text": user_text}]}]}, timeout=10)
        if resp.status_code == 200:
            text = resp.json()['candidates'][0]['content']['parts'][0]['text']
            await update.message.reply_text(text)
        else:
            await update.message.reply_text("Напишите нашему менеджеру: @dmitryprof")
    except:
        await update.message.reply_text("Напишите нашему менеджеру: @dmitryprof")

if __name__ == '__main__':
    # Запуск веб-сервера
    threading.Thread(target=run_web, daemon=True).start()
    
    # Запуск бота
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен и готов к работе!")
    bot_app.run_polling()
