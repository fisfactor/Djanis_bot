import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

# 🔑 Ключи из среды
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🧐 Клиент OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# 🔧 Логгирование
logging.basicConfig(level=logging.INFO)

# 👥 Состояние пользователя
user_specialists = {}
user_first_intro_shown = {}
specialists_data = {}

# 📚 Загрузка конфигураций советников
ADVISORS_PATH = "advisors"

def load_specialists():
    global specialists_data
    for filename in os.listdir(ADVISORS_PATH):
        if filename.endswith(".json"):
            with open(os.path.join(ADVISORS_PATH, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                specialists_data[data["name"]] = data

# 📅 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_specialists.pop(update.effective_user.id, None)
    user_first_intro_shown.pop(update.effective_user.id, None)
    keyboard = [[KeyboardButton(name)] for name in specialists_data.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(🌟 "Выбери Советника для общения:" 🌟, reply_markup=reply_markup)

# 📍 /info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_specialists:
        specialist_name = user_specialists[user_id]
        intro = specialists_data[specialist_name].get("short_intro", "")
        await update.message.reply_text(f"🛏️\n✨ *{specialist_name}* ✨\n\n{intro}", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Пока Советник не выбран. Введи /start и выбери Советника.")

# 💬 Обработка текста
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text.strip()

    if user_message in specialists_data:
        user_specialists[user_id] = user_message
        if user_id not in user_first_intro_shown:
            user_first_intro_shown[user_id] = True
            intro = specialists_data[user_message].get("short_intro", "")
            await update.message.reply_text(f"🛏️\n✨ *{user_message}* ✨\n\n{intro}", parse_mode="Markdown")
        await update.message.reply_text(f"👋 Теперь ты общаешься с Советником: *{user_message}*", parse_mode="Markdown")
        return

    if user_id not in user_specialists:
        await update.message.reply_text("🚷 Сначала выбери Советника через /start 🚷")
        return

    specialist_name = user_specialists[user_id]
    system_prompt = specialists_data[specialist_name].get("system_prompt", "")

    await update.message.reply_text("🔄 Обрабатываю запрос...")

    try:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)

    except Exception as e:
        logging.error(f"❌ Ошибка OpenAI: {e}")
        await update.message.reply_text("⚠️ Ошибка при общении с ИИ. Попробуй позже или проверь API-ключ.")

# ▶️ Запуск

def main():
    load_specialists()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("🚀 Бот запущен и ожидает команд...")
    app.run_polling()

if __name__ == "__main__":
    main()
