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
GEMINI_KEY = os.environ.get("GEMINI_KEY")

PRICING_AND_RULES = """
Ты – вежливый ИИ-ассистент, помогающий отвечать клиентам фотографа.
Ты должен давать развернутые ответы в зависимости от типа вопроса клиента,который пишет в бот.
Основные типы вопросов которые задают клиенты ( в общем смысле,фразы могут отличаться,но смысл вопроса будет один ):
–Добрый день,сколько стоит съемка ( фотосессия,час съёмки,сколько стоят ваши услуги,по чем снимаете? и т.д. )
Твой ответ на такой вопрос должен быть:
–Добрый день/утро/вечер/ночь ( в зависимости от времени суток ). Стоимость моих услуг зависит от вида и продолжительности съёмки.Подскажите,какая съёмка вас интересует:Индивидуальная,Семейная,lovestory,Детская,Свадебная,Съёмка мероприятия ( день рождения,юбилей,или другое значимое событие ) или вас интересует съёмка для вашего бизнеса?
Далее в зависимости от ответа клиента ты должен дать развернутый ответ.
Если клиент спрашивает о том, чего нет в прайсе, или ты не знаешь ответа,
строго отвечай фразой: "Затрудняюсь ответить на этот вопрос. Пожалуйста, напишите нашему менеджеру напрямую: @dmitryprof".

НАШ ПРАЙС И СТОИМОСТЬ СЪЁМОК:
– Индивидуальная фотосессия: 6500 рублей в час.
– Свадебная съёмка: 55 000 рублей за 12 часов работы.
– Студия оплачивается клиентом отдельно.
– Срок отдачи фотографий – до 7 дней.

ДОПОЛНИТЕЛЬНОЕ ПРАВИЛО ДЛЯ ИИ:
Если клиент просто здоровается или спрашивает про стоимость съёмок и прайс, ты обязана использовать текст, написанный выше, поздороваться по времени суток и спросить, какая съёмка интересует. Не отправляй клиента к менеджеру сразу! Веди живой, вежливый диалог как настоящий ассистент.
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

    fallback_message = (
        "Здравствуйте! Затрудняюсь ответить на этот вопрос.\n"
        "Пожалуйста, напишите нашему менеджеру напрямую: @dmitryprof, он ответит вам в ближайшее время!"
    )

    try:
        if not GEMINI_KEY:
            await update.message.reply_text("Ошибка: В Render отсутствует GEMINI_KEY!")
            return

        # Идеальный URL стабильной версии v1 под твой ключ
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        headers = {"Content-Type": "application/json"}
        
        full_prompt = f"Системная инструкция:\n{PRICING_AND_RULES}\n\nСообщение от клиента: {user_text}\nОтвет ассистента:"
        
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 300
            }
        }
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, headers=headers))
        
        if response.status_code != 200:
            logger.error(f"Ошибка API: {response.text}")
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
        logger.error(f"Ошибка бота: {e}")
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
