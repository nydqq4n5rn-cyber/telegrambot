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
HF_TOKEN = os.environ.get("HF_TOKEN")

PRICING_AND_RULES = """
Ты – вежливый ИИ-ассистент, помогающий отвечать клиентам фотографа.
Отвечай коротко, четко, используй только информацию ниже.
Если не знаешь ответа, скажи: "Менеджер скоро свяжется с вами".

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
        if not HF_TOKEN:
            await update.message.reply_text("Ошибка: На сервере Render не настроен HF_TOKEN.")
            return

        # Используем стабильную модель Mistral, которая бесплатна и открыта для всех
        url = "https://api-inference.huggingface.co/models/MistralAI/Mistral-7B-Instruct-v0.3"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        
        prompt_data = f"<s>[INST] {PRICING_AND_RULES}\n\nКлиент пишет: {user_text}\nОтветь клиенту на русском языке коротко: [/INST]"
        
        payload = {
            "inputs": prompt_data,
            "parameters": {"max_new_tokens": 200, "temperature": 0.7}
        }
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, headers=headers))
        result = response.json()
        
        # Hugging Face возвращает список с текстом
        if isinstance(result, list) and len(result) > 0 and 'generated_text' in result[0]:
            full_reply = result[0]['generated_text']
            # Отрезаем сам промпт, чтобы выдать только чистый ответ ИИ
            reply_text = full_reply.split("[/INST]")[-1].strip()
            await update.message.reply_text(reply_text)
        else:
            logger.error(f"HF API Error: {result}")
            await update.message.reply_text("Извините, нейросеть сейчас перезагружается. Попробуйте через минуту.")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_message: {e}")
        await update.message.reply_text("Извините, возникли технические неполадки.")

async def main():
    if not TELEGRAM_TOKEN:
        logger.error("Ошибка: Переменная TELEGRAM_TOKEN не задана!")
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
