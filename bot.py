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

from models import User, SessionLocal

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Переменные окружения
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
DATABASE_URL    = os.environ['DATABASE_URL']      # например postgres://render:…@10.0.x.y:5432/djanis_db
WEBHOOK_URL     = os.environ['WEBHOOK_URL']       # например https://djanis-bot.onrender.com
PORT            = int(os.environ.get('PORT', 8443))

# Администрирование (ID с безлимитным доступом)
ADMIN_IDS = {825403443}

# Инициализация OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Загрузка конфигураций советников из папки advisors
BASE_DIR = os.path.dirname(__file__)
ADVISORS_PATH = os.path.join(BASE_DIR, 'advisors')
specialists = {}
for fname in os.listdir(ADVISORS_PATH):
    if fname.endswith('.json'):
        with open(os.path.join(ADVISORS_PATH, fname), encoding='utf-8') as f:
            data = json.load(f)
            specialists[data['name']] = data

# Хранение текущего советника для каждого чата
active_specialists: dict[int, str] = {}

# Лимиты и оплата

def check_and_update_usage(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    now = datetime.utcnow()
    db = SessionLocal()
    user = db.query(User).filter_by(user_id=user_id).first()
    if not user:
        user = User(user_id=user_id, usage_count=1, last_request=now)
        db.add(user)
        db.commit()
        db.close()
        return True
    # Сброс после 7 дней или ограничение 35 запросов
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
        '⚠️ Тестовый доступ истёк: вы сделали более 35 запросов или прошло 168 часов.\n'
        'Пожалуйста, выберите тариф для продолжения:'
    )
    keyboard = [['7 дней — 300₽', '30 дней — 800₽']]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=markup)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = (
        "Приветствую тебя, живая Душа!\n"
        "Мы — Ваши верные Советники и всегда готовы помочь в решении жизненных задач."
        " Наша миссия — предоставить знания и ответы на любые твои вопросы,"
        " касающиеся различных сфер жизни: Авторское право, Банк, Буквица, Вексель, Транспорт, ЖКХ,"
        " Каноны, КОБ и ДОТУ, Община / Родовые Союзы, Познай-Я, Почта, РодОМ, Суверенитет, Суд, ЗАГС, Траст.\n\n"
        "Чтобы задать свой вопрос, выбери Советника по Имени, соответствующему его знаниям в этой сфере."
        " Советник предоставит ответ в соответствии с его Базой знаний и всегда руководствуется принципами справедливости и этической нравственности.\n\n"
        "Сейчас у тебя бесплатный тестовый доступ: 35 запросов или 168 часов (7 дней)."
        " После окончания тестового периода ты сможешь перейти на расширенный режим.\n\n"
        "Приятного и продуктивного общения!"
    )
    keyboard, row = [], []
    for name in specialists:
        row.append(name)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(welcome_text, reply_markup=markup)

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # Проверка лимитов
    if not check_and_update_usage(user_id):
        await prompt_payment(update)
        return

    # Выбор советника
    if text in specialists:
        active_specialists[chat_id] = text
        await update.message.reply_text(
            f'👋 Теперь вы общаетесь с Советником: <b>{text}</b>',
            parse_mode=ParseMode.HTML
        )
        # Дополнительное приветствие из JSON
        welcome_msg = specialists[text].get('welcome')
        if welcome_msg:
            await update.message.reply_text(welcome_msg)
        return

    # Если советник не выбран
    if chat_id not in active_specialists:
        await update.message.reply_text('Пожалуйста, сначала выберите Советника через /start')
        return

    # Основная логика: запрос к OpenAI
    specialist = specialists[active_specialists[chat_id]]
    base_prompt = specialist.get('system_prompt', '')
    format_instr = (
        '\n\nПожалуйста, форматируй ответ, используя эмодзи, отступы и '  
        'маркированные списки для лучшей читаемости.'
    )
    system_prompt = base_prompt + format_instr

    try:
        response = openai_client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user',   'content': text}
            ],
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply, parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f'❌ Ошибка при запросе к OpenAI: {e}')

# Обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error('Ошибка при обработке запроса', exc_info=context.error)

# Удаление старого вебхука при старте
async def on_startup(app: Application) -> None:
    await app.bot.delete_webhook(drop_pending_updates=True)

# Точка входа
if __name__ == '__main__':
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    app.run_webhook(
        listen='0.0.0.0',
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f'{WEBHOOK_URL}/{TELEGRAM_TOKEN}',
        drop_pending_updates=True
    )
