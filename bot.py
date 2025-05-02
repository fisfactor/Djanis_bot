import os
import json
import logging
from datetime import datetime, timedelta

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

# Зависимости и настройки
logging.basicConfig(level=logging.INFO)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///usage.db')  # SQLite по умолчанию

# Админские user_id — доступ без ограничений
ADMIN_IDS = {123456789}  # Замените на ваш Telegram user_id

# Настройка OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# SQLAlchemy setup
from sqlalchemy import (
    create_engine, Column, BigInteger, Integer, Boolean, DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(BigInteger, primary_key=True, index=True)
    first_ts = Column(DateTime(timezone=True), nullable=False)
    count = Column(Integer, default=0, nullable=False)
    blocked = Column(Boolean, default=False, nullable=False)

# Создадим таблицу при старте
Base.metadata.create_all(bind=engine)

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

# Логика учёта запросов
def check_and_update_usage(user_id: int) -> bool:
    """
    Проверяет и обновляет учёт запросов пользователя.
    Возвращает True, если доступ открыт, False — если заблокирован.
    """
    if user_id in ADMIN_IDS:
        return True

    now = datetime.utcnow()
    db = SessionLocal()
    user = db.get(User, user_id)
    if not user:
        user = User(user_id=user_id, first_ts=now, count=1, blocked=False)
        db.add(user)
        db.commit()
        db.close()
        return True

    if user.blocked:
        db.close()
        return False

    # увеличиваем счётчик
    user.count += 1
    # проверяем условия блокировки
    if user.count >= 35 or (now - user.first_ts) >= timedelta(hours=168):
        user.blocked = True
    db.commit()
    blocked = user.blocked
    db.close()
    return not blocked

async def prompt_payment(update: Update):
    """
    Предлагает пользователю оплатить тарифы после окончания тестового доступа.
    """
    text = (
        "⚠️ Тестовый доступ истёк: вы сделали более 35 запросов или прошло 168 часов.\n"
        "Пожалуйста, выберите один из тарифов для продолжения общения:\n"
    )
    # Простейшие кнопки тарифов
    keyboard = [
        ["7 дней — 300₽", "30 дней — 800₽"],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Приветствие и меню выбора Советника
    """
    welcome_text = (
        "Приветствую тебя, живая Душа!\n"
        "Мы — Ваши верные Советники и всегда готовы помочь..."
    )
    await update.message.reply_text(welcome_text)

    # Клавиатура с кнопками (2 в ряд)
    names = list(specialists.keys())
    keyboard, row = [], []
    for name in names:
        row.append(name)
        if len(row) == 2:
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
    Обработка сообщений и интеграция с учётом лимитов
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Проверяем лимиты
    if not check_and_update_usage(user_id):
        await prompt_payment(update)
        return

    # Выбор Советника
    if text in specialists:
        active_specialists[chat_id] = text
        await update.message.reply_text(
            f"👋 Теперь ты общаешься с Советником: <b>{text}</b>",
            parse_mode=ParseMode.HTML
        )
        # индивидуальное приветствие
        welcome_msg = specialists[text].get('welcome')
        if welcome_msg:
            await update.message.reply_text(welcome_msg)
        return

    # Работа с выбранным Советником
    if chat_id in active_specialists:
        current_name = active_specialists[chat_id]
        specialist = specialists.get(current_name)
        if not specialist:
            await update.message.reply_text("⚠️ Ошибка: Советник не найден.")
            return

        # Форматирование запроса
        base_prompt = specialist.get('system_prompt', '')
        format_instr = (
            "\n\nПожалуйста, форматируй ответ, используя эмодзи, отступы и "
            "маркированные списки для лучшей читаемости."
        )
        system_prompt = base_prompt + format_instr

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": text}
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
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    application.add_error_handler(error_handler)
    application.run_polling()


if __name__ == '__main__':
    main()

