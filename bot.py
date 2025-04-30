
import json
import os
import openai
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Храним активных Советников по chat_id
active_specialists = {}

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
    buttons = list(sorted(specialists.keys()))
    keyboard = [buttons[i:i+2] for i in range(0, len(buttons), 2)]  # две кнопки в строку
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("🌟 Выбери Советника для общения: 🌟", reply_markup=reply_markup)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    current = user_states.get(user_id)
    if current and current in specialists:
        welcome = specialists[current].get("welcome", "Нет информации.")
        await update.message.reply_text(f"📜 Приветствие Советника {current}:\n\n{welcome}")

    else:
        await update.message.reply_text("⚠️ Сначала выбери Советника через команду /start.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip().upper()

    if text in specialists:
        active_specialists[chat_id] = text  # Сохраняем выбор Советника
        user_states[chat_id] = {"advisor": text, "greeted": False}

        specialist = specialists[text]

        if not user_states[chat_id]["greeted"]:
            await update.message.reply_text(specialist.get("welcome", "⚠️ Приветствие не найдено."), parse_mode=ParseMode.HTML)
            user_states[chat_id]["greeted"] = True

        await update.message.reply_text(f"👋 Теперь ты общаешься с Советником: <b>{text}</b>", parse_mode=ParseMode.HTML)

    elif text == "/INFO":
        current = active_specialists.get(chat_id)
        if current and current in specialists:
            await update.message.reply_text(specialists[current].get("welcome", "⚠️ Приветствие не найдено."), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("❓ Сначала выбери Советника через /start.")

    elif chat_id in active_specialists:
        current = active_specialists[chat_id]
        specialist = specialists.get(current)

        if not specialist:
            await update.message.reply_text("⚠️ Возникла ошибка с загрузкой Советника.")
            return

        system_prompt = specialist["system_prompt"]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        )

        reply = response.choices[0].message["content"]
        await update.message.reply_text(reply)

    else:
        await update.message.reply_text("❓ Неизвестный Советник. Пожалуйста, выбери из списка через /start.")


def main():
    app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
