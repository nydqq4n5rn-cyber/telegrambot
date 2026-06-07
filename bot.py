import os
import asyncio
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# Используем токен Hugging Face, который ты уже сделал!
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

        # Меняем модель на сверхлегкую и быструю Qwen, у которой нет проблем с доступностью
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
            # Достаем чистый ответ
            reply_text = full_reply.split("<|im_start|>assistant\n")[-1].replace("<|im_end|>", "").strip()
            await update.message.reply_text(reply_text)
        else:
            # Если модель спит, будим её простым текстовым ответом по прайсу из кода
            if "фотосесси" in user_text.lower() or "сколько стоит" in user_text.lower():
                await update.message.reply_text("Индивидуальная фотосессия стоит 6500 рублей в час. Свадебная съёмка — 55 000 рублей за 12 часов.")
            else:
                await update.message.reply_text("Здравствуйте! Менеджер скоро свяжется с вами для уточнения деталей.")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Индивидуальная фотосессия стоит 6500 рублей в час, свадебная — 55 000 рублей. Менеджер скоро свяжется с вами!")

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
