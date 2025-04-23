import logging
import openai
import time
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# 🔑 ВСТАВЬ СВОИ КЛЮЧИ
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# 🔧 Логгирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ⏱️ Время последнего ответа для каждого пользователя
last_response_time = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я ИИ-ассистент. Задай мне любой вопрос.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()

    # ❌ Антиспам: игнорировать, если пользователь пишет чаще, чем раз в 3 секунды
    if user_id in last_response_time and now - last_response_time[user_id] < 3:
        print("⚠️ Слишком частые сообщения от пользователя {}. Игнор.".format(user_id))
        return

    last_response_time[user_id] = now

    user_message = update.message.text
    print(f"🔎 Получено сообщение от {user_id}: {user_message}")

    await update.message.reply_text("🔄 Обрабатываю запрос...")
    await asyncio.sleep(1)  # заглушка

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)

    except Exception as e:
        print(f"❌ Ошибка при вызове OpenAI: {e}")
        if "Too Many Requests" in str(e) or "429" in str(e):
            await update.message.reply_text("⏱️ Слишком много запросов! Подожди пару секунд.")
        else:
            await update.message.reply_text("⚠️ Произошла ошибка при обращении к ИИ.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
