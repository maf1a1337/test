import aiosqlite
import sqlite3
import os
from config.config import DB_PATH
from dotenv import load_dotenv


def init_env():
    """Инициализация файла .env, если он отсутствует"""
    env_path = os.path.join('config', '.env')
    
    if not os.path.exists('config'):
        os.makedirs('config')
    
    # Проверяем существование файла и наличие необходимых переменных
    if not os.path.exists(env_path) or not all([os.getenv('BOT_TOKEN'), os.getenv('DB_PATH')]):
        print("\n=== Настройка конфигурации бота ===")
        
        # Получаем существующие значения, если они есть
        existing_token = os.getenv('BOT_TOKEN', '')
        existing_db_path = os.getenv('DB_PATH', 'santa_bot.db')
        
        # Запрашиваем BOT_TOKEN
        while True:
            bot_token = input(f"\nВведите токен бота (текущий: {existing_token or 'отсутствует'})\n"
                            "Получить токен можно у @BotFather в Telegram: ")
            if bot_token.strip():
                break
            print("❌ Токен не может быть пустым!")
        
        # Запрашиваем DB_PATH
        db_path = input(f"\nВведите путь к файлу базы данных (Enter для значения по умолчанию: {existing_db_path})\n"
                       "Путь к базе данных: ")
        db_path = db_path.strip() if db_path.strip() else existing_db_path
        
        # Записываем значения в файл .env
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(f"BOT_TOKEN={bot_token}\n")
            f.write(f"DB_PATH={db_path}\n")
        
        print("\n✅ Файл конфигурации успешно создан!")
        
        # Перезагружаем переменные окружения
        load_dotenv(env_path)
    else:
        # Загружаем существующие переменные окружения
        load_dotenv(env_path)
        print("✅ Конфигурация загружена успешно")

def init_app():
    """Инициализация приложения: создание необходимых файлов и папок"""
    print("\n=== Инициализация приложения ===")
    init_env()  # Инициализация .env
    init_db()   # Инициализация базы данных
    print("\n=== Инициализация завершена ===\n")

def init_db():
    """Инициализация базы данных: создание файла и таблиц, если они отсутствуют."""
    if not os.path.exists(DB_PATH):
        print("База данных не найдена. Создаём новую базу данных...")
        with sqlite3.connect(DB_PATH) as db:
            cursor = db.cursor()

            # Таблица пользователей
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                connection_date TEXT
            )
            """)

            # Таблица для связывания Санты и получателя
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS santa_recipient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                santa_id INTEGER,
                recipient_id INTEGER,
                id_box INTEGER,
                FOREIGN KEY (santa_id) REFERENCES users(user_id),
                FOREIGN KEY (recipient_id) REFERENCES users(user_id)
            )
            """)

            # Таблица для желаний пользователей
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_wish (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                user_wish TEXT,
                user_adds TEXT,
                id_box INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """)

            # Таблица для коробок
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS santa_box (
                id_box INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                box_name TEXT,
                box_photo TEXT,
                box_desc TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """)

            db.commit()

async def add_user(user_id: int, username: str, connection_date: str):
    """Асинхронное добавление пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT OR IGNORE INTO users (user_id, username, connection_date)
        VALUES (?, ?, ?)
        """, (user_id, username, connection_date))
        await db.commit()


async def add_box(user_id: int, box_name: str, box_photo: str, box_desc: str) -> int:
    """Асинхронное добавление ко��обки. Возвращает id созданной коробки."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
        INSERT INTO santa_box (user_id, box_name, box_photo, box_desc)
        VALUES (?, ?, ?, ?)
        """, (user_id, box_name, box_photo, box_desc))
        await db.commit()
        return cursor.lastrowid  # Возвращаем id созданной коробки

async def delete_box(id_box: int):
    """Удаление коробки и всех связанных записей"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM santa_box WHERE id_box = ?", (id_box,))
        await db.execute("DELETE FROM santa_recipient WHERE id_box = ?", (id_box,))
        await db.execute("DELETE FROM user_wish WHERE id_box = ?", (id_box,))
        await db.commit()

async def get_box_participants(id_box: int):
    """Получение списка участников коробки"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT DISTINCT uw.user_id, uw.user_name
            FROM user_wish uw
            WHERE uw.id_box = ?
        """, (id_box,))
        return await cursor.fetchall()

async def remove_participant(user_id: int, id_box: int):
    """Удаление участника из коробки"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            DELETE FROM user_wish 
            WHERE user_id = ? AND id_box = ?
        """, (user_id, id_box))
        await db.execute("""
            DELETE FROM santa_recipient 
            WHERE (santa_id = ? OR recipient_id = ?) AND id_box = ?
        """, (user_id, user_id, id_box))
        await db.commit()

async def is_box_owner(user_id: int, id_box: int) -> bool:
    """Проверка является ли пользователь владельцем коробки"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT 1 FROM santa_box 
            WHERE id_box = ? AND user_id = ?
        """, (id_box, user_id))
        return bool(await cursor.fetchone())

async def create_santa_pairs(id_box: int):
    """Создание пар Санта-Получатель"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем список участников
        cursor = await db.execute("""
            SELECT user_id FROM user_wish 
            WHERE id_box = ?
        """, (id_box,))
        participants = [row[0] for row in await cursor.fetchall()]
        
        if len(participants) < 2:
            return None
        
        # Перемешиваем список получателей
        import random
        recipients = participants.copy()
        while True:
            random.shuffle(recipients)
            # Проверяем, что никто не дарит сам себе
            if not any(s == r for s, r in zip(participants, recipients)):
                break
        
        # Очищаем старые пары для этой коробки
        await db.execute("""
            DELETE FROM santa_recipient 
            WHERE id_box = ?
        """, (id_box,))
        
        # Создаем новые пары
        pairs = list(zip(participants, recipients))
        await db.executemany("""
            INSERT INTO santa_recipient (santa_id, recipient_id, id_box)
            VALUES (?, ?, ?)
        """, [(santa, recipient, id_box) for santa, recipient in pairs])
        
        await db.commit()
        return pairs

async def get_user_info(user_id: int):
    """Получение информации о пользователе"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT user_id, username, connection_date
            FROM users
            WHERE user_id = ?
        """, (user_id,))
        user_data = await cursor.fetchone()
        
        if user_data:
            return {
                'user_id': user_data[0],
                'username': user_data[1],
                'connection_date': user_data[2]
            }
        return None

async def get_box_info(box_id: int):
    """Получение информации о коробке"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id_box, box_name, box_desc, box_photo
            FROM santa_box
            WHERE id_box = ?
        """, (box_id,))
        row = await cursor.fetchone()
        
        if row:
            return {
                'id_box': row[0],
                'box_name': row[1],
                'box_desc': row[2],
                'box_photo': row[3]
            }
        return None

async def is_participant(user_id: int, box_id: int) -> bool:
    """Проверка является ли пользователь участником коробки"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT 1 FROM user_wish
            WHERE user_id = ? AND id_box = ?
        """, (user_id, box_id))
        return bool(await cursor.fetchone())

async def add_participant(user_id: int, name: str, address: str, box_id: int, wish: str):
    """Добавление участника в коробку"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO user_wish (user_id, user_name, user_adds, id_box, user_wish)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, name, address, box_id, wish))
            await db.commit()
            print(f"Участник добавлен: user_id={user_id}, box_id={box_id}")  # Для отладки
    except Exception as e:
        print(f"Ошибка при добавлении в базу данных: {e}")
        raise

async def update_participant_info(user_id: int, box_id: int, field: str, value: str):
    """Обновление информации участника"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"""
            UPDATE user_wish
            SET {field} = ?
            WHERE user_id = ? AND id_box = ?
        """, (value, user_id, box_id))
        await db.commit()

async def get_participating_boxes(user_id: int):
    """Получение списка коробок, в которых пользователь является участником"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT DISTINCT sb.id_box, sb.box_name, sb.box_desc
            FROM santa_box sb
            JOIN user_wish uw ON sb.id_box = uw.id_box
            WHERE uw.user_id = ?
        """, (user_id,))
        rows = await cursor.fetchall()
        return [{'id_box': row[0], 'box_name': row[1], 'box_desc': row[2]} for row in rows]

async def get_created_boxes(user_id: int):
    """Получение списка коробок, созданных пользователем"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT id_box, box_name, box_desc, box_photo
            FROM santa_box 
            WHERE user_id = ?
            ORDER BY id_box DESC
        """, (user_id,))
        boxes = await cursor.fetchall()
        return [dict(row) for row in boxes] if boxes else []

async def get_participant_info(user_id: int, box_id: int):
    """Получение информации об участнике в конкретной коробке"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT user_name, user_adds, user_wish
            FROM user_wish
            WHERE user_id = ? AND id_box = ?
        """, (user_id, box_id))
        row = await cursor.fetchone()
        
        if row:
            return {
                'user_name': row[0],
                'user_adds': row[1],
                'user_wish': row[2]
            }
        return None