
import json
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Путь к директории с конфигурациями
ADVISORS_PATH = "./advisors"

# Загружаем конфигурации всех Советников
def load_specialists():
    specialists = {}
    for filename in os.listdir(ADVISORS_PATH):
        if filename.endswith(".json"):
            with open(os.path.join(ADVISORS_PATH, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                key = data.get("name", "").upper()
                specialists[key] = data
    return specialists

specialists = load_specialists()
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[s] for s in sorted(specialists.keys())]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🌟 Выбери Советника для общения: 🌟", reply_markup=reply_markup)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    current = user_states.get(user_id)
    if current and current in specialists:
        welcome = specialists[current].get("welcome", "Нет информации.")
        await update.message.reply_text(f"📜 Приветствие Советника {current}:{welcome}")
    else:
        await update.message.reply_text("⚠️ Сначала выбери Советника через команду /start.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    text = update.message.text.upper()

    if text in specialists:
        previous = user_states.get(user_id)
        user_states[user_id] = text

        if text != previous:
            welcome = specialists[text].get("welcome", "Рад встрече!")
            await update.message.reply_text(f"📜 {welcome}")

        await update.message.reply_text(f"👋 Теперь ты общаешься с Советником: {text}")
    else:
        await update.message.reply_text("❓ Неизвестный Советник. Пожалуйста, выбери из списка через /start.")

def main():
    app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
