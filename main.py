import os
import time
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from telegram.ext.filters import Text
import json
from src.export import export2xlsx
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from src.g_collector import scheduled_clear_tables

# Состояния для ConversationHandler
ST_POINT, END_POINT = range(2)
LOGIN, PASSWORD = range(2)

load_dotenv()



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Я бот. Чем могу помочь?')

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Напиши логин')
    return LOGIN  # Переходим к состоянию LOGIN

async def get_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_login = update.message.text
    context.user_data['user_login'] = user_login  # Сохраняем логин
    await update.message.reply_text('Напиши пароль')
    return PASSWORD  # Переходим к состоянию PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_pass = update.message.text
    user_login = context.user_data.get('user_login')  # Получаем логин, который был введен ранее

    if user_login != os.getenv("LOGIN_USER") or user_pass != os.getenv("LOGIN_PASSWORD"):
        await update.message.reply_text('Неправильный логин или пароль')
        return ConversationHandler.END  # Завершаем разговор
    else:
        context.user_data["authenticated"] = True  # Помечаем пользователя как авторизованного
        await update.message.reply_text('Авторизация прошла успешно')
        return ConversationHandler.END  # Завершаем разговор

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Авторизация отменена')
    return ConversationHandler.END

async def target_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file2exp):
    file_path = os.path.join(os.getcwd(), 'data', file2exp)

        # Проверяем, существует ли файл
    if os.path.exists(file_path):
            # Отправляем файл пользователю
        with open(file_path, 'rb') as file:
            await update.message.reply_document(document=file)
    else:
            await update.message.reply_text('Файл не найден.')


# Команда /export доступна только авторизованным пользователям
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data.get("authenticated"):  # Проверяем, авторизован ли пользователь
        await update.message.reply_text('Укажи диапазон в формате "st_p-end_p", например: 14-17')
        return ST_POINT  # Переходим к состоянию для обработки диапазона
    else:
        await update.message.reply_text('Для доступа к этой команде необходимо авторизоваться!')
        return ConversationHandler.END

async def get_st_and_end_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        # Получаем сообщение от пользователя и парсим его
        user_input = update.message.text.strip()
        if "-" not in user_input:
            raise ValueError("Диапазон должен быть в формате 'st_p-end_p'.")

        st_point, end_point = map(int, user_input.split("-"))  # Разделяем и конвертируем в числа
        if st_point >= end_point:
            raise ValueError("Начало периода должно быть меньше конца периода.")

        context.user_data['st_point'] = st_point
        context.user_data['end_point'] = end_point

        # Формируем имя файла
        file_name = f"courier_data_{st_point}-{end_point}.xlsx"

        # Отправляем сообщение о процессе формирования файла
        await update.message.reply_text(f'Формирую файл: {file_name}')
        export2xlsx(file_name, st_point, end_point)
        time.sleep(5)
        await target_file(update, context, file_name)

        return ConversationHandler.END  # Завершаем разговор
    except ValueError as e:
        await update.message.reply_text(f'Ошибка: {e}. Попробуй снова указать диапазон в формате "st_p-end_p".')
        return ST_POINT  # Если ошибка, просим пользователя ввести диапазон снова

async def take_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    print(user_message)

app = ApplicationBuilder().token(os.getenv("TOKEN")).build()

# Создаем ConversationHandler для команды export
export_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('export', export)],  # Точка входа для команды export
    states={
        ST_POINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_st_and_end_points)],  # Обработка диапазона
    },
    fallbacks=[CommandHandler('cancel', cancel)]  # Обработчик для отмены
)

# Добавляем ConversationHandler для команды export
app.add_handler(export_conversation_handler)

# Создаем ConversationHandler для логина
login_conversation_handler = ConversationHandler(
    entry_points=[CommandHandler('login', login)],  # Точка входа для команды login
    states={
        LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_login)],  # Состояние для логина
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],  # Состояние для пароля
    },
    fallbacks=[CommandHandler('cancel', cancel)]  # Обработчик для отмены
)

# Добавляем ConversationHandler для логина
app.add_handler(login_conversation_handler)

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_clear_tables, 'interval', minutes=60)
scheduler.start()

# Команды
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(Text(), take_message))
print("Бот запущен...")


app.run_polling()
