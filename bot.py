import os
import json
import logging
from datetime import datetime, timedelta

from openai import OpenAI
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from sqlalchemy import create_engine, Column, BigInteger, Integer, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# Логирование
logging.basicConfig(level=logging.INFO)

# Переменные окружения
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///usage.db')
WEBHOOK_URL = os.environ['WEBHOOK_URL']  # e.g. https://your-service.onrender.com
PORT = int(os.environ.get('PORT', '8443'))

# Админские ID (безлимитный доступ)
ADMIN_IDS = {825403443}

# Клиент OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Настройка базы данных
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    is_admin = Column(Boolean, default=False)
    last_request = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Загрузка советников
BASE_DIR = os.path.dirname(__file__)
ADVISORS_PATH = os.path.join(BASE_DIR, "advisors")
specialists = {}
for fname in os.listdir(ADVISORS_PATH):
    if fname.endswith('.json'):
        with open(os.path.join(ADVISORS_PATH, fname), encoding='utf-8') as f:
            data = json.load(f)
            specialists[data['name']] = data

active_specialists: dict[int, str] = {}

# Управление лимитами и оплатой
from datetime import datetime

def check_and_update_usage(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    now = datetime.utcnow()
    db = SessionLocal()
    user = db.get(User, user_id)
    if not user:
        user = User(user_id=user_id, usage_count=1, last_request=now)
        db.add(user)
        db.commit()
        db.close()
        return True
    if user.usage_count >= 35 or (now - user.last_request) >= timedelta(hours=168):
        db.close()
        return False
    user.usage_count += 1
    user.last_request = now
    db.commit()
    db.close()
    return True

async def prompt_payment(update: Update) -> None:
    text = (
        "⚠️ Тестовый доступ истёк: вы сделали более 35 запросов или прошло 168 часов.\n"
        "Пожалуйста, выберите один из тарифов для продолжения общения:"  )
    keyboard = [["7 дней — 300₽", "30 дней — 800₽"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=markup)

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard, row = [], []
    for name in specialists:
        row.append(name)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👋 Выберите Советника для общения:", reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if not check_and_update_usage(user_id):
        await prompt_payment(update)
        return

    if text in specialists:
        active_specialists[chat_id] = text
        await update.message.reply_text(
            f"👋 Теперь ты общаешься с Советником: <b>{text}</b>",
            parse_mode=ParseMode.HTML
        )
        return

    if chat_id not in active_specialists:
        await update.message.reply_text("Пожалуйста, сначала выберите Советника через /start")
        return

    specialist = specialists[active_specialists[chat_id]]
    # TODO: здесь логика запроса к OpenAI и отправки ответа

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Ошибка при обработке запроса", exc_info=context.error)

# Удаление старого вебхука
async def on_startup(app: Application) -> None:
    await app.bot.delete_webhook(drop_pending_updates=True)

# Точка входа
if __name__ == "__main__":
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
        drop_pending_updates=True
    )
