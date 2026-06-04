import os
import asyncio
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# Настраиваем логирование, чтобы видеть всё в консоли Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация токенов
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

SYSTEM_INSTRUCTION = """
Ты – вежливый и профессиональный ИИ-ассистент, помогающий отвечать клиентам.
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

    # Обработка команды /start
    if user_text == "/start":
        await update.message.reply_text(
            "Здравствуйте! Я ваш ИИ-помощник. Помогаю отвечать клиентам.\n"
            "Задайте мне любой вопрос о стоимости или условиях съёмки, и я отвечу!"
        )
        return

    # Запрос к Gemini по HTTP (для обхода европейской блокировки на Render)
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": user_text}]}],
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]}
        }
        
        # Запускаем обычный запрос в асинхронном режиме
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, headers=headers))
        result = response.json()
        
        reply_text = result['candidates'][0]['content']['parts'][0]['text']
        await update.message.reply_text(reply_text)
        
    except Exception as e:
        logger.error(f"Ошибка Gemini: {e}")
        await update.message.reply_text("Извините, возникли технические неполадки. Попробуйте еще раз.")

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("Ошибка: Переменная TELEGRAM_TOKEN не задана!")
        return

    # Настройка Flask
    app = Flask('')

    @app.route('/')
    def home():
        return "Бот работает!"

    # Запуск Flask-сервера
    port = int(os.environ.get('PORT', 10000))
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', port, app)
    
    # Запускаем веб-сервер в фоновом режиме asyncio
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, server.serve_forever)
    logger.info("Веб-сервер Flask успешно запущен.")

    # Настройка Телеграм-бота
    logger.info("Запуск бота Telegram...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", handle_message))
    
    # Инициализируем и запускаем бота без конфликта потоков
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    # Оставляем бота работать бесконечно
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
