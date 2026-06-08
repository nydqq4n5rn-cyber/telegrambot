import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

# Берем ключ из переменных окружения (в Render он должен быть прописан в Environment Variables)
GEMINI_KEY = os.environ.get("GEMINI_KEY")

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

    # Железная страховка на приветствия
    greeting_words = ["привет", "здравствуй", "добрый день", "добрый вечер", "доброе утро", "стоимость", "цена", "прайс", "сколько стоит"]
    if any(word in user_lower for word in greeting_words):
        await update.message.reply_text(
            "Добрый день! Стоимость моих услуг зависит от вида и продолжительности съёмки. \n"
            "Подскажите, какая съёмка вас интересует: Индивидуальная, Семейная, Lovestory, Детская, Свадебная, "
            "Съёмка мероприятия (день рождения, юбилей) или вас интересует съёмка для вашего бизнеса?"
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

        # ИСПРАВЛЕНО: Стабильный URL (v1 вместо v1beta) для защиты от ошибки 404
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        headers = {"Content-Type": "application/json"}
        
        # ИСПРАВЛЕНО: Чистая структура payload для защиты от ошибки 400
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": user_text}
                    ]
                }
            ]
        }

        # Отправляем запрос к ИИ Google Gemini
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            res_data = response.json()
            # Достаем текст ответа из структуры JSON Gemini
            try:
                ai_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                await update.message.reply_text(ai_text)
            except (KeyError, IndexError):
                await update.message.reply_text(fallback_message)
        else:
            # Если сервер вернул ошибку, бот сообщит её код
            await update.message.reply_text(f"Ошибка сервера ИИ (Код {response.status_code}). Проверь ключ или настройки.")

    except Exception as e:
        print(f"Ошибка при запросе к Gemini: {e}")
        await update.message.reply_text(fallback_message)
