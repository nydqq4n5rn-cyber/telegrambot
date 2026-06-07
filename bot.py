import os
import asyncio
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

PRICING_AND_RULES = """
Ты – вежливый ИИ-ассистент, помогающий отвечать клиентам фотографа.
Ты должен давать развернутые ответы в зависимости от типа вопроса клиента.

НАШ ПРАЙС И СТОИМОСТЬ СЪЁМОК:
– Индивидуальная фотосессия: 6500 рублей в час.
– Свадебная съёмка: 55 000 рублей за 12 часов работы.
– Студия оплачивается клиентом отдельно.
– Срок отдачи фотографий – до 7 дней.

Если клиент спрашивает о том, чего нет в прайсе, строго отвечай фразой: "Затрудняюсь ответить на этот вопрос. Пожалуйста, напишите нашему менеджеру напрямую: @dmitryprof".
"""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text

    if user_text == "/start":
        await update.message.reply_text(
            "Здравствуйте! Я ваш ИИ-помощник. Помогаю отвечать клиентам.\n"
            "Задайте мне любой вопрос о стоимости или условиях съёмки, и я отвечу!"
        )
        return

    try:
        if not GEMINI_KEY:
            await update.message.reply_text("Ошибка: В Render отсутствует GEMINI_KEY!")
            return

        # Используем самый стабильный URL v1beta
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        headers = {"Content-Type": "application/json"}
        
        full_prompt = f"Системная инструкция:\n{PRICING_AND_RULES}\n\nСообщение от клиента: {user_text}\nОтвет ассистента:"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }]
        }
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, headers=headers))
        
        # Если Гугл ответил ошибкой (например, плохой ключ)
        if response.status_code != 200:
            await update.message.reply_text(f"Гугл вернул ошибку сервера (Код {response.status_code}): {response.text[:150]}")
            return
            
        result = response.json()
        
        if "candidates" in result and len(result["candidates"]) > 0:
            reply_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            if reply_text:
                await update.message.reply_text(reply_text)
                return

        await update.message.reply_text("Здравствуйте! Затрудняюсь ответить на этот вопрос. Пожалуйста, напишите менеджеру: @dmitryprof")
        
    except Exception as e:
        logger.error(f"Ошибка бота: {e}")
        await update.message.reply_text(f"Произошла техническая ошибка в коде: {e}")

async def main():
    if not TELEGRAM_TOKEN:
        return

    app = Flask('')

    @app.route('/')
    def home():
        return "Бот работает!"

    port = int(os.environ.get('PORT', 10000))
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', port, app)
    
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, server.serve_forever)

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", handle_message))
    
    await application.initialize()
    await application.start()
    
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.updater.start_polling(drop_pending_updates=True)
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
