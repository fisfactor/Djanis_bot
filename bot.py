import os
import json
import logging
from datetime import datetime, timedelta
# импорт для расчёта срока
from dateutil.relativedelta import relativedelta
from openai import OpenAI
from telegram import Update, ReplyKeyboardMarkup
# импорт для inline-клавиатур
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from models import User, SessionLocal

# ————— Конфигурация тарифов —————
TARIFFS = {
    'БМ': ('Базовый на месяц',     50),
    'БГ': ('Базовый на год',      350),
    'РМ': ('Расширенный на месяц',300),
    'РГ': ('Расширенный на год',  2200),
}

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Переменные окружения
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
DATABASE_URL    = os.environ['DATABASE_URL']      
WEBHOOK_URL     = os.environ['WEBHOOK_URL']       
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

ALL_ADVISORS = list(specialists.keys())

# Хранение текущего советника для каждого чата
active_specialists: dict[int, str] = {}

# Лимиты и оплата

def check_and_update_usage(user_id: int) -> bool:
    now = datetime.utcnow()
    db  = SessionLocal()
    user = db.query(User).filter_by(user_id=user_id).first()

    if not user:
        # записываем оба поля одинаково при первом обращении
        user = User(
            user_id=user_id,
            usage_count=1,
            first_request=now,
            last_request=now,
            is_admin=(user_id in ADMIN_IDS),
            tariff_paid=True
        )
        db.add(user)
        db.commit()
        db.close()
        return True

    # уже есть запись
    # админам не считаем лимиты
    if user.is_admin:
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

    # ————— проверяем оплату тарифа —————
    # сначала регистрируем / проверяем тестовый запрос
    if not check_and_update_usage(user_id):
        # бесплатный лимит упёрся — просим оплатить
        await prompt_payment(update)
        return

    # после этого точно есть user в БД (либо только что создан),
    # можно дальше работать с тарифами и проверкой истечения
    db   = SessionLocal()
    user = db.query(User).filter_by(user_id=user_id).first()
    db.close()

    if not user or not user.tariff_paid:
        return await update.message.reply_text(
            "У вас нет активного тарифа. Выберите /tariff и дождитесь подтверждения оплаты."
        )
    # ————— сброс таймера при первом запросе после оплаты —————
    if user.last_request < user.first_request:
        db   = SessionLocal()
        u_db = db.query(User).filter_by(user_id=user_id).first()
        u_db.first_request = datetime.utcnow()
        db.commit(); db.close()
    # ————— проверяем срок действия —————
    expires = user.tariff_expires()
    if expires and expires < datetime.utcnow():
        db   = SessionLocal()
        u_db = db.query(User).filter_by(user_id=user_id).first()
        u_db.tariff_paid = False
        db.commit(); db.close()
        return await update.message.reply_text("Срок вашего тарифа истёк. Повторите выбор /tariff")
    # —————————————————————————————————————

    # Смена Советника — не считаем за запрос
    if text in specialists:
    # ————— для «базового» тарифа проверяем список выбранных советников —————
         if user.tariff in ('БМ','БГ') and text not in user.advisors:
             return await update.message.reply_text(
                 "Этот советник не входит в ваш пакет. Сначала выберите /advisors"
         )
    # ——————————————————————————————————————————————————————————————— 
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

    # Проверка лимитов
    if not check_and_update_usage(user_id):
        await prompt_payment(update)
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
        # —————— НОВЫЙ БЛОК: считаем остаток лимита ——————
        # достаём текущего пользователя
        db = SessionLocal()
        user = db.query(User).filter_by(user_id=user_id).first()
        db.close()

        # считаем, сколько осталось запросов и часов
        max_requests = 35
        max_hours    = 168
        left_requests = max_requests - (user.usage_count if user else 0)
        elapsed       = datetime.utcnow() - (user.first_request if user else datetime.utcnow())
        left_hours    = max_hours - (elapsed.total_seconds() / 3600)

        footer = (
            f"\n\n🔎 Осталось запросов: {left_requests}  "
            f"⏳ Осталось времени: {left_hours:.1f} ч"
        )

        # отправляем ответ + footer
        await update.message.reply_text(
            reply + footer,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f'❌ Ошибка при запросе к OpenAI: {e}')


# ————— Новый хэндлер выбора тарифа —————
async def cmd_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
     kb = InlineKeyboardMarkup(row_width=2)
     for code,(name,price) in TARIFFS.items():
         kb.insert(InlineKeyboardButton(f"{name} — {price}₽", callback_data=f"tariff|{code}"))
     await update.message.reply_text("Выберите тариф:", reply_markup=kb)

async def on_tariff_chosen(cq):
     code = cq.data.split('|',1)[1]
     db   = SessionLocal()
     user = db.query(User).filter_by(user_id=cq.from_user.id).first()
     user.tariff      = code
     user.tariff_paid = False
     user.advisors    = []
     db.commit(); db.close()
     await cq.answer(f"Выбран тариф «{TARIFFS[code][0]}». Ожидайте подтверждения оплаты.")
# —————————————————————————————————————

async def cmd_advisors(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
     user = SessionLocal().query(User).filter_by(user_id=update.effective_user.id).first()
     if user.tariff not in ('БМ','БГ'):
         return await update.message.reply_text("У вас расширенный пакет — доступны все советники.")
     kb = InlineKeyboardMarkup(row_width=4)
     for name in ALL_ADVISORS:
         kb.insert(InlineKeyboardButton(
             f"{'✅ ' if name in user.advisors else ''}{name}",
             callback_data=f"adv|{name}"
         ))
     await update.message.reply_text("Выберите до двух советников:", reply_markup=kb)

async def on_adv_choice(cq):
     name = cq.data.split('|',1)[1]
     db   = SessionLocal()
     user = db.query(User).filter_by(user_id=cq.from_user.id).first()
     if name in user.advisors:
         user.advisors.remove(name)
     else:
         if len(user.advisors) >= 2:
             return await cq.answer("Нельзя выбрать более двух.", show_alert=True)
         user.advisors.append(name)
     db.commit(); db.close()
     await cq.answer(f"Текущий выбор: {', '.join(user.advisors) or '—'}")
# —————————————————————————————————————

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
    # Регистрация новых хэндлеров
    app.add_handler(CommandHandler('tariff', cmd_tariff))
    # ловим колбэк от inline-кнопки «tariff|…»
    app.add_handler(CallbackQueryHandler(on_tariff_chosen, pattern=r'^tariff\|'))
    app.add_handler(CommandHandler('advisors', cmd_advisors))
    # ловим колбэк от inline-кнопки «adv|…»
    app.add_handler(CallbackQueryHandler(on_adv_choice,   pattern=r'^adv\|'))

    app.run_webhook(
        listen='0.0.0.0',
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f'{WEBHOOK_URL}/{TELEGRAM_TOKEN}',
        drop_pending_updates=True
    )
