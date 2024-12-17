import os
import time
import logging
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

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,  # Уровень логирования (можно изменить на DEBUG для более детализированных логов)
    handlers=[
        logging.FileHandler('bot.log'),  # Запись в файл 'bot.log'
        logging.StreamHandler()  # Также вывод в консоль
    ]
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду '/start'. Отправляет приветственное сообщение пользователю.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.

    Returns:
        None
    """
    logger.info(f"Received /start command from {update.message.chat_id}")
    await update.message.reply_text('Привет! Я бот. Чем могу помочь?')


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду '/login'. Запрашивает у пользователя логин.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.

    Returns:
        int: Состояние для ConversationHandler (LOGIN).
    """
    logger.info(f"User {update.message.chat_id} initiated login process.")
    await update.message.reply_text('Напиши логин')
    return LOGIN  # Переходим к состоянию LOGIN


async def get_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получает логин от пользователя и запрашивает пароль.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.

    Returns:
        int: Состояние для ConversationHandler (PASSWORD).
    """
    user_login = update.message.text
    context.user_data['user_login'] = user_login  # Сохраняем логин
    logger.info(f"User {update.message.chat_id} entered login: {user_login}")
    await update.message.reply_text('Напиши пароль')
    return PASSWORD  # Переходим к состоянию PASSWORD


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получает пароль от пользователя и проверяет авторизацию.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.

    Returns:
        int: Статус завершения разговора или продолжения в зависимости от проверки логина и пароля.
    """
    user_pass = update.message.text
    user_login = context.user_data.get('user_login')  # Получаем логин, который был введен ранее

    if user_login != os.getenv("LOGIN_USER") or user_pass != os.getenv("LOGIN_PASSWORD"):
        logger.warning(f"Failed login attempt for user {update.message.chat_id}")
        await update.message.reply_text('Неправильный логин или пароль')
        return ConversationHandler.END  # Завершаем разговор
    else:
        context.user_data["authenticated"] = True  # Помечаем пользователя как авторизованного
        logger.info(f"User {update.message.chat_id} successfully authenticated")
        await update.message.reply_text('Авторизация прошла успешно')
        return ConversationHandler.END  # Завершаем разговор


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду '/cancel'. Завершает процесс авторизации и завершает разговор.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.

    Returns:
        int: Завершение разговора (ConversationHandler.END).
    """
    logger.info(f"User {update.message.chat_id} cancelled the login process.")
    await update.message.reply_text('Авторизация отменена')
    return ConversationHandler.END


async def target_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file2exp):
    """
    Отправляет файл пользователю, если файл существует.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.
        file2exp (str): Имя файла, который нужно отправить пользователю.

    Returns:
        None
    """
    file_path = os.path.join(os.getcwd(), 'data', file2exp)
    logger.info(f"Attempting to send file {file2exp} to user {update.message.chat_id}")

    # Проверяем, существует ли файл
    if os.path.exists(file_path):
        # Отправляем файл пользователю
        with open(file_path, 'rb') as file:
            await update.message.reply_document(document=file)
        logger.info(f"File {file2exp} successfully sent to user {update.message.chat_id}")
    else:
        logger.error(f"File {file2exp} not found for user {update.message.chat_id}")
        await update.message.reply_text('Файл не найден.')


async def export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает команду '/export'. Запрашивает у пользователя диапазон для формирования отчета.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.

    Returns:
        int: Состояние для ConversationHandler (ST_POINT).
    """
    if context.user_data.get("authenticated"):  # Проверяем, авторизован ли пользователь
        logger.info(f"User {update.message.chat_id} initiated export process.")
        await update.message.reply_text('Укажи диапазон в формате "st_p-end_p", например: 14-17')
        return ST_POINT  # Переходим к состоянию для обработки диапазона
    else:
        logger.warning(f"Unauthorized access attempt by user {update.message.chat_id}")
        await update.message.reply_text('Для доступа к этой команде необходимо авторизоваться!')
        return ConversationHandler.END


async def get_st_and_end_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Получает диапазон от пользователя и генерирует файл с данными.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.

    Returns:
        int: Завершение разговора или повторный запрос диапазона в случае ошибки.
    """
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
        logger.info(f"Generating file {file_name} for user {update.message.chat_id}")
        await update.message.reply_text(f'Формирую файл: {file_name}')
        export2xlsx(file_name, st_point, end_point)
        time.sleep(5)
        await target_file(update, context, file_name)

        return ConversationHandler.END  # Завершаем разговор
    except ValueError as e:
        logger.error(f"Invalid input from user {update.message.chat_id}: {e}")
        await update.message.reply_text(f'Ошибка: {e}. Попробуй снова указать диапазон в формате "st_p-end_p".')
        return ST_POINT  # Если ошибка, просим пользователя ввести диапазон снова


async def take_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Логирует все сообщения, которые поступают от пользователя.

    Args:
        update (Update): Объект обновления, содержащий информацию о сообщении.
        context (ContextTypes.DEFAULT_TYPE): Контекст, содержащий данные о текущем разговоре.

    Returns:
        None
    """
    user_message = update.message.text
    logger.info(f"User {update.message.chat_id} sent message: {user_message}")


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
logger.info("Bot started...")

app.run_polling()
