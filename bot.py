import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логов
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение переменных из Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здравствуйте! Я помощник фотографа. Чем могу помочь?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    user_lower = user_text.lower()
    
    # 1. Прайс-лист (База знаний бота)
    price_info = (
        "Вот актуальные цены:\n"
        "• Индивидуальная фотосессия: 6500 руб./час.\n"
        "• Свадебная съёмка: 55 000 руб. за 12 часов.\n"
        "Важные условия:\n"
        "– Студия оплачивается клиентом отдельно.\n"
        "– Срок отдачи фотографий – до 7 дней."
    )

    # 2. Быстрые ответы без ИИ
    trigger_words = ["цена", "прайс", "сколько стоит", "индивидуальная", "свадебная", "съёмка"]
    if any(word in user_lower for word in trigger_words):
        await update.message.reply_text(f"Добрый день! {price_info}\n\nПодскажите, что именно вас интересует?")
        return

    # 3. Умный ответ через ИИ
    system_instruction = (
        "Ты — профессиональный помощник фотографа. "
        "Твои цены: Индивидуальная 6500р/час, Свадебная 55000р за 12 часов работы. "
        "Условия: студия оплачивается клиентом отдельно, срок отдачи фото — до 7 дней. "
        "Отвечай вежливо и кратко. Если спрашивают что-то, чего нет в твоей базе — перенаправляй к менеджеру: @dmitryprof."
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        payload = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}]
        }
        
        response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=10)
        
        if response.status_code == 200:
            ai_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            await update.message.reply_text(ai_text)
        else:
            await update.message.reply_text("Напишите, пожалуйста, нашему менеджеру: @dmitryprof")
            
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        await update.message.reply_text("Напишите нашему менеджеру напрямую: @dmitryprof")

def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        print("Ошибка: Отсутствуют переменные окружения TELEGRAM_TOKEN или GEMINI_KEY")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен...")
    app.run_polling()

if __name__ == '__main__':
    main()
