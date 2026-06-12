import os
import requests
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка Flask для «обмана» Render (чтобы он не убивал сервис)
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Настройка бота
logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

async def start(update, context):
    await update.message.reply_text("Здравствуйте! Я помощник фотографа.")

async def handle_message(update, context):
    user_text = update.message.text
    # Логика ответов
    await update.message.reply_text("Принято, я обрабатываю ваш запрос...")

if __name__ == '__main__':
    # 1. Запускаем веб-сервер в отдельном потоке
    threading.Thread(target=run_web, daemon=True).start()
    
    # 2. Запускаем бота
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен!")
    bot_app.run_polling()
