import aiosqlite
import os

DB_PATH = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 5000,
                last_bonus TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                referrer_id INTEGER
            )
        """)
        # Безопасно добавляем колонку, если база данных уже существовала без неё
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS nfts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                name TEXT,
                level INTEGER DEFAULT 1,
                is_equipped INTEGER DEFAULT 0,
                position INTEGER DEFAULT 0
            )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def add_user(user_id, username, referrer_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            exists = await cursor.fetchone()
        if not exists:
            await db.execute(
                "INSERT INTO users (user_id, username, balance, referrer_id) VALUES (?, ?, ?, ?)", 
                (user_id, username or "User", 5000, referrer_id)
            )
            await db.commit()
            return True  # Пользователь новый
        return False  # Пользователь уже существовал

async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def update_last_bonus(user_id, timestamp):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (timestamp, user_id))
        await db.commit()

async def get_top_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10") as cursor:
            return await cursor.fetchall()

async def set_ban(user_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (status, user_id))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users") as cursor:
            return await cursor.fetchall()
