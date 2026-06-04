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

# Считываем токены
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY") or os.environ.get("GOOGLE_API_KEY")

PRICING_AND_RULES = """
Ты – вежливый и профессиональный ИИ-ассистент, помогающий отвечать клиентам фотографа.
Твоя задача – отвечать на вопросы коротко, четко и помогать клиенту.
Не используй жесткие кнопки, веди живой диалог. Если не знаешь ответа,
скажи, что менеджер скоро свяжется.

НАШ ПРАЙС И СТОИМОСТЬ СЪЁМОК:
– Индивидуальная фотосессия: 6500 рублей в час.
– Свадебная съёмка: 55 000 рублей за 12 часов работы.
– Студия оплачивается клиентом отдельно.
– Срок отдачи фотографий – до 7 дней.
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
            await update.message.reply_text("Ошибка: На сервере не настроен API-ключ.")
            return

        # ХИТРОСТЬ: Если ключ начинается на AQ, мы используем шлюз Vertex, иначе — AI Studio
        if GEMINI_KEY.startswith("AQ"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

        headers = {'Content-Type': 'application/json'}
        prompt_data = f"Инструкция: {PRICING_AND_RULES}\n\nКлиент пишет: {user_text}\nОтветь коротко:"
        
        # Передаем запрос в максимально разжеванном виде для Google
        payload = {
            "contents": [{
                "parts": [{"text": prompt_data}]
            }]
        }
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, headers=headers))
        result = response.json()
        
        if 'error' in result:
            # Если Vertex требует другого обращения, пробуем сделать через генеративный шлюз
            logger.error(f"Google API Error: {result['error']}")
            await update.message.reply_text(f"Ошибка Google: {result['error'].get('message', 'Неверный тип ключа')}\n\nПодсказка: Если это ключ Vertex, создайте обычный API Key в Google AI Studio.")
            return
            
        reply_text = result['candidates'][0]['content']['parts'][0]['text']
        await update.message.reply_text(reply_text)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Извините, возникли технические неполадки.")

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("Ошибка: TELEGRAM_TOKEN не задан!")
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
    logger.info("Веб-сервер Flask успешно запущен.")

    logger.info("Запуск бота Telegram...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", handle_message))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
