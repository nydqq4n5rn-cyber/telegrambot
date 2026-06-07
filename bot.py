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

# Юзернейм папы для перенаправления клиентов
PAPA_USERNAME = "@dmitryprof"

# ВАШ ПРОМТ С ПАПОЙ ДО ЕДИНОГО СЛОВА + СТРАХОВКА ОТ СБОЕВ
PRICING_AND_RULES = f"""
Ты – вежливый ИИ-ассистент, помогающий отвечать клиентам фотографа.
Ты должен давать развернутые ответы в зависимости от типа вопроса клиента,который пишет в бот.
Основные типы вопросов которые задают клиенты ( в общем смысле,фразы могут отличаться,но смысл вопроса будет один ):
–Добрый день,сколько стоит съемка ( фотосессия,час съёмки,сколько стоят ваши услуги,по чем снимаете? и т.д. )
Твой ответ на такой вопрос должен быть:
–Добрый день/утро/вечер/ночь ( ты должен выбрать тот вариант времени суток,в зависимости от времени когда пришло такое сообщение по МСК ).Стоимость моих услуг зависит от вида и продолжительности съёмки.Подскажите,какая съёмка вас интересует:Индивидуальная,Семейная,lovestory,Детская,Свадебная,Съёмка мероприятия ( день рождения,юбилей,или другое значимое событие ) или вас интересует съёмка для вашего бизнеса?
Далее в зависимости от ответа клиента ты должен дать развернутый ответ. вот примерные ответы клиентов (в общем смысле,фразы могут отличаться,но смысл ответа будет один )
Если клиент спрашивает о том, чего нет в прайсе, или ты не знаешь ответа,
строго отвечай фразой: "Затрудняюсь ответить на этот вопрос. Пожалуйста, напишите нашему менеджеру напрямую: {{PAPA_USERNAME}}".

НАШ ПРАЙС И СТОИМОСТЬ СЪЁМОК:
– Индивидуальная фотосессия: 6500 рублей в час.
– Свадебная съёмка: 55 000 рублей за 12 часов работы.
– Студия оплачивается клиентом отдельно.
– Срок отдачи фотографий – до 7 дней.

ДОПОЛНИТЕЛЬНОЕ ПРАВИЛО ДЛЯ ИИ:
Если клиент просто здоровается («Привет», «Здравствуйте») или спрашивает про стоимость съёмок и прайс, ты обязана использовать текст, написанный выше, поздороваться по времени суток и спросить, какая съёмка интересует. Не отправляй клиента к менеджеру сразу, если его вопрос касается обычного прайса или приветствия!
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

    # Текст-заглушка, если нейросеть зависнет
    fallback_message = (
        f"Здравствуйте! Затрудняюсь ответить на этот вопрос.\n"
        f"Пожалуйста, напишите нашему менеджеру напрямую: {PAPA_USERNAME}, он ответит вам в ближайшее время!"
    )

    try:
        if not HF_TOKEN:
            await update.message.reply_text(fallback_message)
            return

        url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        
        prompt_data = f"<|im_start|>system\n{PRICING_AND_RULES}<|im_end|>\n<|im_start|>user\n{user_text}<|im_end|>\n<|im_start|>assistant\n"
        
        payload = {
            "inputs": prompt_data,
            "parameters": {"max_new_tokens": 150, "temperature": 0.5}
        }
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, headers=headers))
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0 and 'generated_text' in result[0]:
            full_reply = result[0]['generated_text']
            reply_text = full_reply.split("<|im_start|>assistant\n")[-1].replace("<|im_end|>", "").strip()
            
            if not reply_text:
                await update.message.reply_text(fallback_message)
            else:
                await update.message.reply_text(reply_text)
        else:
            # Ручная подстраховка, если модель временно перегружена
            user_lower = user_text.lower()
            if any(word in user_lower for word in ["сколько стоит", "стоимость", "цена", "прайс", "съемка", "фотосессия"]):
                await update.message.reply_text(
                    "Стоимость моих услуг зависит от вида и продолжительности съёмки. "
                    "Подскажите, какая съёмка вас интересует: Индивидуальная, Семейная, lovestory, Детская, Свадебная, Съёмка мероприятия или съёмка для вашего бизнеса?"
                )
            else:
                await update.message.reply_text(fallback_message)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
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
