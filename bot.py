import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Инициализация токенов из настроек Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

# Настройка API ключа для Gemini
genai.configure(api_key=GEMINI_KEY)

# Инструкция для нейросети и прайс-лист папы
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

# Словарь для хранения истории диалогов
chats = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text

    # Обработка кнопки СТАРТ (красивое приветствие без вызова ИИ)
    if user_text == "/start":
        await update.message.reply_text(
            "Здравствуйте! Я ваш ИИ-помощник. Помогаю отвечать клиентам.\n"
            "Задайте мне любой вопрос о стоимости или условиях съёмки, и я отвечу!"
        )
        return

    # Создание сессии диалога с Gemini, если её ещё нет для этого пользователя
    if chat_id not in chats:
        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_INSTRUCTION
            )
            chats[chat_id] = model.start_chat(history=[])
        except Exception as e:
            print(f"Ошибка создания модели Gemini: {e}")
            await update.message.reply_text("Извините, возникли технические неполадки с подключением к ИИ.")
            return

    # Отправка вопроса в нейросеть с обязательным await
    try:
        response = await chats[chat_id].send_message_async(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Ошибка Gemini при генерации ответа: {e}")
        await update.message.reply_text("Извините, возникли технические неполадки. Попробуйте еще раз.")

def main():
    if not TELEGRAM_TOKEN:
        print("Ошибка: Переменная TELEGRAM_TOKEN не задана в Render!")
        return

    # Создание веб-сервера Flask, чтобы Render видел, что проект "жив"
    app = Flask('')

    @app.route('/')
    def home():
        return "Бот успешно запущен и работает!"

    def run_flask():
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

    # Запуск веб-сервера в фоновом потоке
    threading.Thread(target=run_flask, daemon=True).start()

    print("Бот запущен...")
    
    # Настройка и запуск самого Телеграм-бота
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики сообщений и команды /start
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("start", handle_message))
    
    # Запускаем чтение сообщений, сбрасывая старые зависшие запросы
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
