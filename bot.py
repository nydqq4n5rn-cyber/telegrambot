import os
import asyncio
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
# Официальный модуль от Google — теперь никаких ошибок в JSON!
import google.generativeai as genai

# Настраиваем логирование, чтобы видеть всё в панели Render
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Считываем токены из настроек Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY") or os.environ.get("GOOGLE_API_KEY")

# Инструкции для папиного бота
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

# Инициализируем Google API через официальный метод
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text

    # Команда /start срабатывает мгновенно
    if user_text == "/start":
        await update.message.reply_text(
            "Здравствуйте! Я ваш ИИ-помощник. Помогаю отвечать клиентам.\n"
            "Задайте мне любой вопрос о стоимости или условиях съёмки, и я отвечу!"
        )
        return

    try:
        if not GEMINI_KEY:
            await update.message.reply_text("Ошибка: На сервере Render не настроен API-ключ GEMINI_KEY.")
            return

        # Подключаем официальную модель со встроенной системной инструкцией
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=PRICING_AND_RULES
        )
        
        # Запускаем генерацию в отдельном потоке, чтобы бот не зависал и не ловил Conflict
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(user_text))
        
        # Отправляем чистый ответ клиенту
        await update.message.reply_text(response.text)
        
    except Exception as e:
        logger.error(f"Ошибка в handle_message: {e}")
        await update.message.reply_text("Извините, возникли технические неполадки. Попробуйте еще раз.")

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("Ошибка: Переменная TELEGRAM_TOKEN не задана!")
        return

    # Поднимаем Flask веб-сервер, чтобы Render держал бота активным
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

    # Настраиваем и запускаем Telegram-бота
    logger.info("Запуск бота Telegram...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", handle_message))
    
    await application.initialize()
    await application.start()
    
    # Жестко сбрасываем старые зависшие копии бота в Телеграме, чтобы НЕ БЫЛО ошибки Conflict
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.updater.start_polling(drop_pending_updates=True)
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
