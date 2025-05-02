import os
import json
import logging
from openai import OpenAI
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Путь к папке с JSON-файлами Советников
BASE_DIR = os.path.dirname(__file__)
ADVISORS_PATH = os.path.join(BASE_DIR, "advisors")

# Загрузка всех Советников из JSON
specialists = {}
for filename in os.listdir(ADVISORS_PATH):
    if filename.endswith('.json'):
        filepath = os.path.join(ADVISORS_PATH, filename)
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
            specialists[data['name']] = data

# Словарь для хранения выбранного Советника на каждый чат
active_specialists: dict[int, str] = {}

# Инициализируем клиент OpenAI
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Стартовое сообщение — выводим список доступных Советников кнопками
    """
    names = list(specialists.keys())
    # Формируем клавиатуру по 3 кнопки в ряд
    keyboard = []
    row = []
    for name in names:
        row.append(name)
        if len(row) >= 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Выберите Советника для общения:",
        reply_markup=markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка входящих текстовых сообщений
    """
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Выбор Советника
    if text in specialists:
        active_specialists[chat_id] = text
        await update.message.reply_text(
            f"👋 Теперь ты общаешься с Советником: <b>{text}</b>",
            parse_mode=ParseMode.HTML
        )
        return

    # Если Советник выбран, перенаправляем сообщение в OpenAI
    if chat_id in active_specialists:
        current_name = active_specialists[chat_id]
        specialist = specialists.get(current_name)
        if not specialist:
            await update.message.reply_text("⚠️ Ошибка: Советник не найден.")
            return

        system_prompt = specialist.get('system_prompt', '')
        user_text = text
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # или "gpt-4o-mini"
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_text}
                ],
            )
            reply = response.choices[0].message.content
            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при запросе к OpenAI: {e}")
        return

    # Если Советник не выбран
    await update.message.reply_text(
        "⚠️ Сначала выберите Советника командой /start"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")


def main():
    token = os.getenv('TELEGRAM_TOKEN')
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)

    # Запуск polling
    application.run_polling()


if __name__ == '__main__':
    main()

