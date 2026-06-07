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

# Считываем токены из Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

SYSTEM_INSTRUCTION = """
Ты – вежливый ИИ-ассистент, помогающий отвечать клиентам фотографа Дмитрия.
Веди живой, вежливый и естественный диалог как настоящий человек-помощник.

НАШ ПРАЙС И СТОИМОСТЬ СЪЁМОК:
– Индивидуальная фотосессия: 6500 рублей в час. В стоимость входит час съёмки и отдача фото до 7 дней. Студия оплачивается клиентом отдельно.
– Свадебная съёмка: 55 000 рублей за 12 часов работы. Отдача фото до 7 дней.

ПРАВИЛА ОТВЕТА ДЛЯ ИИ:
1. Если клиент выбрал индивидуальную или свадебную съёмку, подробно распиши ему цену из прайса выше и спроси, сориентировать ли его по свободным датам.
2. Если клиент спрашивает о том, чего нет в прайсе, или ты не знаешь точного ответа, строго и без лишних слов отвечачай фразой: 
"Затрудняюсь ответить на этот вопрос. Пожалуйста, напишите нашему менеджеру напрямую: @dmitryprof".
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

    user_lower = user_text.lower()
    
    # Железная страховка: если клиент просто здоровается или спрашивает про цену вообще,
    # выдаем готовую папину фразу сразу же без запросов к ИИ.
    greeting_words = ["привет", "здравствуй", "добрый день", "добрый вечер", "доброе утро", "стоимость", "цена", "прайс", "сколько стоит"]
    if any(word in user_lower for word in greeting_words):
        await update.message.reply_text(
            "Добрый день! Стоимость моих услуг зависит от вида и продолжительности съёмки. "
            "Подскажите, какая съёмка вас интересует: Индивидуальная, Семейная, lovestory, Детская, Свадебная, "
            "Съёмка мероприятия (день рождения, юбилей, или другое значимое событие) или вас интересует съёмка для вашего бизнеса?"
        )
        return

    fallback_message = (
        "Здравствуйте! Затрудняюсь ответить на этот вопрос.\n"
        "Пожалуйста, напишите нашему менеджеру напрямую: @dmitryprof, он ответит вам в ближайшее время!"
    )

    try:
        if not GEMINI_KEY:
            await update.message.reply_text("Ошибка: В Render отсутствует GEMINI_KEY!")
            return

        # Официальный стабильный URL v1
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        headers = {"Content-Type": "application/json"}
        
        # Передаем правила в специальном поле systemInstruction, как требует Google
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_text}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            },
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 300
            }
        }
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, headers=headers))
        
        if response.status_code != 200:
            logger.error(f"Ошибка API Gemini: {response.text}")
            await update.message.reply_text(fallback_message)
            return
            
        result = response.json()
        
        if "candidates" in result and len(result["candidates"]) > 0:
            reply_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            if reply_text:
                await update.message.reply_text(reply_text)
                return

        await update.message.reply_text(fallback_message)
        
    except Exception as e:
        logger.error(f"Ошибка в коде бота: {e}")
        await update.message.reply_text(fallback_message)

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
