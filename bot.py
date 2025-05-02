import os
import json
import logging
import openai
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

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
            # Ожидаем, что в файле есть поле "name"
            specialists[data['name']] = data

# Словарь для хранения выбранного Советника на каждый чат
active_specialists: dict[int, str] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Стартовое сообщение — выводим список доступных Советников
    """
    names = '\n'.join(f"- {name}" for name in specialists.keys())
    text = "👋 Выбери Советника для общения:\n" + names
    await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка входящих текстовых сообщений
    """
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # 1) Выбор Советника
    if text in specialists:
        active_specialists[chat_id] = text
        await update.message.reply_text(
            f"👋 Теперь ты общаешься с Советником: <b>{text}</b>",
            parse_mode=ParseMode.HTML
        )
        return

    # 2) Дополнительная команда /INFO
    elif text.upper() == "/INFO":
        info = (
            "ℹ️ Список команд:\n"
            "- Напиши имя Советника для начала диалога\n"
            "- /INFO — показать это сообщение\n"
            "- Другие сообщения будут пересылаться выбранному Советнику"
        )
        await update.message.reply_text(info)
        return

    # 3) Работа с выбранным Советником
    elif chat_id in active_specialists:
        user_text = text
        current_name = active_specialists[chat_id]
        specialist = specialists.get(current_name)
        if not specialist:
            await update.message.reply_text("⚠️ Ошибка: Советник не найден.")
            return

        # Получаем системную подсказку для OpenAI
        system_prompt = specialist.get('system_prompt', '')

        # Устанавливаем API-ключ OpenAI из переменных окружения
        openai.api_key = os.getenv('OPENAI_API_KEY')
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # или "gpt-4o-mini"
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_text}
                ]
            )
            reply = response.choices[0].message.content
            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при запросе к OpenAI: {e}")
        return

    # 4) Неизвестная команда
    else:
        await update.message.reply_text(
            "⚠️ Неизвестная команда. Напиши /start для начала."
        )
        return

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    Логирование ошибок, чтобы не получать "No error handlers are registered"
    """
    logging.error(f"Update {update} caused error {context.error}")


def main():
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)

    # Токен Telegram-бота
    token = os.getenv('TELEGRAM_TOKEN')

    # Создаем приложение
    application = ApplicationBuilder().token(token).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    # Старт бота
    application.run_polling()


if __name__ == '__main__':
    main()

