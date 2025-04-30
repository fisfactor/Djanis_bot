import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
logging.basicConfig(level=logging.INFO)

user_specialists = {}
user_first_intro_shown = {}
specialists_data = {}
ADVISORS_PATH = "advisors"

def load_specialists():
    global specialists_data
    for filename in os.listdir(ADVISORS_PATH):
        if filename.endswith(".json"):
            with open(os.path.join(ADVISORS_PATH, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
                specialists_data[data["name"]] = data

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_specialists.pop(update.effective_user.id, None)
    user_first_intro_shown.pop(update.effective_user.id, None)
    keyboard = [[KeyboardButton(name)] for name in sorted(specialists_data.keys())]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("\U0001F31F Выбери Советника для общения: \U0001F31F", reply_markup=reply_markup)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_specialists:
        specialist_name = user_specialists[user_id]
        intro = specialists_data[specialist_name].get("short_intro", "")
        await update.message.reply_text(f"\U0001F6CF\n\u2728 *{specialist_name}* \u2728\n\n{intro}", parse_mode="Markdown")
    else:
        await update.message.reply_text("\u274C Пока Советник не выбран. Введи /start и выбери Советника.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text.strip()

    if user_message in specialists_data:
        user_specialists[user_id] = user_message
        if user_id not in user_first_intro_shown:
            user_first_intro_shown[user_id] = True
            intro = specialists_data[user_message].get("short_intro", "")
            await update.message.reply_text(f"\U0001F6CF\n\u2728 *{user_message}* \u2728\n\n{intro}", parse_mode="Markdown")
        await update.message.reply_text(f"\U0001F44B Теперь ты общаешься с Советником: *{user_message}*", parse_mode="Markdown")
        return

    if user_id not in user_specialists:
        await update.message.reply_text("\U0001F6B7 Сначала выбери Советника через /start \U0001F6B7")
        return

    specialist_name = user_specialists[user_id]
    system_prompt = specialists_data[specialist_name].get("system_prompt", "")

    await update.message.reply_text("\U0001F504 Обрабатываю запрос...")

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
        logging.error(f"\u274C Ошибка OpenAI: {e}")
        await update.message.reply_text("\u26A0\ufe0f Ошибка при обращении к ИИ. Попробуй позже или проверь API-ключ.")

def main():
    load_specialists()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("\U0001F680 Бот запущен и ожидает команд...")
    app.run_polling()

if __name__ == "__main__":
    main()
