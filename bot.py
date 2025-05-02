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
    Приветственное сообщение и меню выбора Советника
    """
    # Краткое приветствие для пользователя
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
    await update.message.reply_text(welcome_text)

    # Клавиатура с кнопками (2 в ряд)
    names = list(specialists.keys())
    keyboard = []
    row = []
    for name in names:
        row.append(name)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )
    await update.message.reply_text(
        "👋 Выберите Советника для общения:",
        reply_markup=markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Если нажата кнопка-Советник
    if text in specialists:
        active_specialists[chat_id] = text
        await update.message.reply_text(
            f"👋 Теперь ты общаешься с Советником: <b>{text}</b>",
            parse_mode=ParseMode.HTML
        )
        # Дополнительное индивидуальное сообщение из JSON (если есть)
        specialist = specialists[text]
        welcome_msg = specialist.get('welcome')
        if welcome_msg:
            await update.message.reply_text(welcome_msg)
        return

    # Если Советник выбран, отправляем запрос в OpenAI
    if chat_id in active_specialists:
        current_name = active_specialists[chat_id]
        specialist = specialists.get(current_name)
        if not specialist:
            await update.message.reply_text("⚠️ Ошибка: Советник не найден.")
            return

        base_prompt = specialist.get('system_prompt', '')
        # Получаем системную подсказку и добавляем инструкцию по форматированию
        # Получаем базовую системную подсказку из JSON и добавляем инструкцию по оформлению
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

    # Если до этого не выбран Советник
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

    application.run_polling()


if __name__ == '__main__':
    main()
