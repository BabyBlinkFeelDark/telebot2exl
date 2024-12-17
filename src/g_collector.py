import shutil, os
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Установите временную зону
local_tz = pytz.timezone('Europe/Moscow')  # Укажите ваш часовой пояс
load_dotenv()
# Получение текущего времени в вашем часовом поясе
def get_local_time():
    return datetime.now(local_tz)

def is_within_time_range(start_hour, start_minute, end_hour, end_minute):
    now = get_local_time()
    start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    end_time = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    return start_time <= now <= end_time


def scheduled_clear_tables():
    if is_within_time_range(3,30,6,0):
        print(f"Очистка начата в {get_local_time()}...")
        cleaner(os.path.join(os.getcwd()[:-3], "data") )
    else:
        print(f"Очистка пропущена в {get_local_time()}: вне диапазона или таблицы пусты.")

def cleaner(folder_path):
    try:
        shutil.rmtree(folder_path)
        print(f"Папка {folder_path} с содержимым успешно удалена.")
    except FileNotFoundError:
        print(f"Папка {folder_path} не найдена.")
    except PermissionError:
        print(f"Недостаточно прав для удаления папки {folder_path}.")

