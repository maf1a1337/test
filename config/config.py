import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv(os.path.join("config", ".env"))

# Получаем значения из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH")
