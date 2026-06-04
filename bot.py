import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google.generativeai as genai

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")

genai.configure(api_key=GEMINI_KEY)

SYSTEM_INSTRUCTION = """
Ты — вежливый и профессиональный ИИ-ассистент, помогающий отвечать клиентам. 
Твоя задача — отвечать на вопросы коротко, четко и помогать клиенту. 
Не используй жесткие кнопки, веди живой диалог. Если не знаешь ответа, 
скажи, что менеджер скоро свяжется.
"""

chats = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in chats:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )
        chats[chat_id] = model.start_chat(history=[])

    try:
        response = chats[chat_id].send_message(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("Извините, возникли технические неполадки.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    application.run_polling(drop_pending_updates=True)