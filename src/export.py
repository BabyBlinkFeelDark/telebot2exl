import os
from src.bot_db import fetch_courier_data_to_excel
from dotenv import load_dotenv

load_dotenv()


def export2xlsx(file, st_point, end_point):
    """
    Экспортирует данные о курьерах в формат Excel.

    Функция подключается к базе данных с использованием параметров из окружения,
    извлекает данные о курьерах в заданном диапазоне времени (start_point, end_point),
    и сохраняет их в файл Excel в папку "data" в корневом каталоге проекта.

    Параметры:
    file (str): Имя выходного Excel файла (например, "couriers_data.xlsx").
    st_point (datetime): Начальная точка временного диапазона для выборки данных.
    end_point (datetime): Конечная точка временного диапазона для выборки данных.

    Возвращает:
    None: Функция сохраняет данные в указанный файл, не возвращая значения.

    Пример использования:
    export2xlsx("couriers_data.xlsx", "2024-01-01 00:00:00", "2024-01-31 23:59:59")
    """
    # Конфигурация базы данных
    DB_CONFIG = {
        "host": os.getenv("HOST"),  # Укажите хост
        "port": os.getenv("PORT"),  # Укажите порт
        "user": os.getenv("USER_NAME"),  # Укажите пользователя
        "password": os.getenv("PASSWORD"),  # Укажите пароль
        "database": os.getenv("DBNAME"),  # Укажите базу данных
    }

    # Путь к выходному файлу
    DATA_DIR = os.path.join(os.getcwd(), "data")  # Путь к папке data в корне
    os.makedirs(DATA_DIR, exist_ok=True)  # Создать папку, если она не существует

    OUTPUT_FILE = os.path.join(DATA_DIR, file)  # Путь к файлу

    # Вызов функции экспорта
    fetch_courier_data_to_excel(st_point, end_point,
                                host=DB_CONFIG["host"],
                                port=DB_CONFIG["port"],
                                user=DB_CONFIG["user"],
                                password=DB_CONFIG["password"],
                                database=DB_CONFIG["database"],
                                output_file=OUTPUT_FILE,
                                )

    print(f"Данные успешно сохранены в файле: {OUTPUT_FILE}")
