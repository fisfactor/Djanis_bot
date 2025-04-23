import os
import logging
import time
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import openai

# 🔑 Ключи
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# 🔧 Логгирование
logging.basicConfig(level=logging.INFO)

# 👤 Хранилище ассистентов по user_id
user_specialists = {}

# 📋 Ассистенты и их стили
specialists = {
    "ВИЗУАЛЫ": "Ты — AI-Генератор визуалов. Помогаешь создавать креативные идеи для дизайна, Reels и Stories. Говори вдохновляюще, с изюминкой.",
    "ПРАВОВЕД": "Ты — AI-Правовед Защитник Человека. Даёшь советы по вексельному, правовому и юридическому суверенитету, говоришь с уверенностью и уважением.",
    "ВЕКСЕЛЬ": "Ты — AI-Ассистент по Вексельному праву. Отвечаешь по шаблонам, юридически точно, с отсылками к международным нормам.",
    "ЛИЧНОСТЬ": "Ты — AI-Помощник Личностного Роста. Говоришь мягко, вдохновляюще, с метафорами, помогая человеку раскрыться и развиваться."
}

# 🧭 Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("ВИЗУАЛЫ"), KeyboardButton("ПРАВОВЕД")],
        [KeyboardButton("ВЕКСЕЛЬ"), KeyboardButton("ЛИЧНОСТЬ")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выбери, с каким ассистентом ты хочешь общаться:", reply_markup=reply_markup)

# 🧠 Запомнить выбор ассистента
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    user_id = update.effective_user.id
    if choice in specialists:
        user_specialists[user_id] = choice
        await update.message.reply_text(f"Теперь ты общаешься с ассистентом: {choice}")
    else:
        await handle_message(update, context)  # если текст — обычное сообщение

# 💬 Ответ ассистента
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    specialist = user_specialists.get(user_id)

    if not specialist:
        await update.message.reply_text("Сначала выбери ассистента через /start 🙏")
        return

    style_prompt = specialists[specialist]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": style_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message["content"]
        await update.message.reply_text(reply)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await update.message.reply_text("Произошла ошибка при обращении к ИИ 😔")

# ▶️ Запуск
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_choice))

    print("🚀 Мульти-бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
