import os
import logging
import time
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import openai

# 🔑 Получаем ключи из переменных среды
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# 🔧 Логгирование
logging.basicConfig(level=logging.INFO)

# 👥 Состояние пользователей
user_specialists = {}

# 📋 Стиль общения каждого ассистента
specialists = {
    "🎨 ВИЗУАЛЫ": "Ты — AI-Генератор визуалов. Помогаешь придумывать креативные идеи для Reels, Stories и визуального контента. Опиши визуально, вдохновляюще, с метафорами.",
    "⚖️ ПРАВОВЕД": "Ты — AI-Правовед. Защищаешь права Человека, опираясь на международные нормы, говоришь официальным и уверенным языком.",
    "📜 ВЕКСЕЛЬ": "Ты — AI-ассистент по вексельному праву. Отвечаешь строго юридически, даёшь ссылки на статьи и нормы права.",
    "🌱 ЛИЧНОСТЬ": "Ты — AI-Помощник Личностного Роста. Помогаешь Человеку раскрыться, обрести гармонию и связь с Творцом. Используй мягкий тон, образы, метафоры."
}

# 🟢 /start — выбор ассистента
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🎨 ВИЗУАЛЫ"), KeyboardButton("⚖️ ПРАВОВЕД")],
        [KeyboardButton("📜 ВЕКСЕЛЬ"), KeyboardButton("🌱 ЛИЧНОСТЬ")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выбери ассистента для общения:", reply_markup=reply_markup)

# ✍️ Обработка текста и запоминание выбора
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text.strip()

    if user_message in specialists:
        user_specialists[user_id] = user_message
        await update.message.reply_text(f"Теперь ты общаешься с ассистентом: {user_message}")
        return

    if user_id not in user_specialists:
        await update.message.reply_text("Сначала выбери ассистента через /start 🙏")
        return

    specialist = user_specialists[user_id]
    system_prompt = specialists[specialist]

    await update.message.reply_text("🔄 Обрабатываю запрос...")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message["content"]
        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"❌ Ошибка OpenAI: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при обращении к ИИ. Попробуй позже или проверь API-ключ.")

# ▶️ Запуск бота
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("🚀 Бот запущен и ожидает команды...")
    app.run_polling()

if __name__ == "__main__":
    main()
