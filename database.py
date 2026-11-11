import aiosqlite
import time

DB_NAME = "pets.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                pet_name TEXT,
                pet_photo TEXT,
                pet_char TEXT,
                age INTEGER DEFAULT 0,
                hunger INTEGER DEFAULT 100,
                thirst INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                mood INTEGER DEFAULT 100,
                coins INTEGER DEFAULT 100,
                is_sick INTEGER DEFAULT 0,
                is_dirty INTEGER DEFAULT 0,
                is_dead INTEGER DEFAULT 0,
                last_update INTEGER
            )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def create_user(user_id, name, photo_id, char):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, pet_name, pet_photo, pet_char, last_update)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, name, photo_id, char, int(time.time())))
        await db.commit()

async def update_pet(user_id, **kwargs):
    if not kwargs:
        return
    fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        await db.commit()

async def add_coins(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

# Функция для просчета времени (чтобы шкалы падали, даже если бот лежал)
def calculate_decay(last_update, current_time):
    elapsed_minutes = (current_time - last_update) / 60
    # 1% падает каждые 5 минут (для теста можно сделать быстрее)
    drop = int(elapsed_minutes / 5) 
    return drop