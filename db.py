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
                referrer_id INTEGER,
                ton REAL DEFAULT 0.0
            )
        """)
        # Безопасно добавляем новые колонки к существующей таблице пользователей
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN ton REAL DEFAULT 0.0")
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
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                buyer_id INTEGER,
                nft_id INTEGER,
                price_ton REAL,
                status TEXT DEFAULT 'pending'
            )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            res = await cursor.fetchone()
            if res and len(res) < 7:
                # Если в возвращенном кортеже нет колонки TON (из-за кэша сессии или старого соединения)
                # Возвращаем расширенную запись
                lst = list(res)
                while len(lst) < 7:
                    lst.append(0.0)
                return tuple(lst)
            return res

async def add_user(user_id, username, referrer_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            exists = await cursor.fetchone()
        if not exists:
            await db.execute(
                "INSERT INTO users (user_id, username, balance, referrer_id, ton) VALUES (?, ?, ?, ?, 0.0)", 
                (user_id, username or "User", 5000, referrer_id)
            )
            await db.commit()
            return True  # Пользователь новый
        return False  # Пользователь уже существовал

async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def update_ton(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET ton = ton + ? WHERE user_id = ?", (amount, user_id))
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

# --- NFT МЕТОДЫ ---

async def get_user_nfts(owner_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM nfts WHERE owner_id = ?", (owner_id,)) as cursor:
            return await cursor.fetchall()

async def get_nft(nft_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM nfts WHERE id = ?", (nft_id,)) as cursor:
            return await cursor.fetchone()

async def find_nft_by_name(owner_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        # Ищем без учета регистра
        async with db.execute("SELECT * FROM nfts WHERE owner_id = ? AND LOWER(name) = LOWER(?) LIMIT 1", (owner_id, name)) as cursor:
            return await cursor.fetchone()

async def add_nft(owner_id, name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO nfts (owner_id, name, level, is_equipped, position) VALUES (?, ?, 1, 0, 0)", (owner_id, name))
        await db.commit()

async def update_nft_owner(nft_id, new_owner_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE nfts SET owner_id = ?, is_equipped = 0, position = 0 WHERE id = ?", (new_owner_id, nft_id))
        await db.commit()

async def update_nft_level(nft_id, new_level):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE nfts SET level = ? WHERE id = ?", (new_level, nft_id))
        await db.commit()

async def equip_nft(nft_id, position):
    async with aiosqlite.connect(DB_PATH) as db:
        # Сначала открепляем все NFT с этой же позиции для этого же владельца
        async with db.execute("SELECT owner_id FROM nfts WHERE id = ?", (nft_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            owner_id = row[0]
            await db.execute("UPDATE nfts SET is_equipped = 0, position = 0 WHERE owner_id = ? AND position = ?", (owner_id, position))
        
        await db.execute("UPDATE nfts SET is_equipped = 1, position = ? WHERE id = ?", (position, nft_id))
        await db.commit()

async def unequip_nft(owner_id, position):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE nfts SET is_equipped = 0, position = 0 WHERE owner_id = ? AND position = ?", (owner_id, position))
        await db.commit()

async def resolve_user(identifier):
    # Поиск по ID или username
    async with aiosqlite.connect(DB_PATH) as db:
        if identifier.isdigit():
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (int(identifier),)) as cursor:
                return await cursor.fetchone()
        
        # Очищаем username от @ и ссылки
        username = identifier.replace("@", "").strip()
        if "t.me/" in username:
            username = username.split("t.me/")[-1]
            
        async with db.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,)) as cursor:
            return await cursor.fetchone()

# --- СДЕЛКИ МЕТОДЫ ---

async def create_deal(seller_id, buyer_id, nft_id, price_ton):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO deals (seller_id, buyer_id, nft_id, price_ton, status) VALUES (?, ?, ?, ?, 'pending')",
                         (seller_id, buyer_id, nft_id, price_ton))
        await db.commit()

async def get_user_deals(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        # Возвращает сделки, где пользователь продавец или покупатель
        async with db.execute("SELECT * FROM deals WHERE (seller_id = ? OR buyer_id = ?) AND status = 'pending'", (user_id, user_id)) as cursor:
            return await cursor.fetchall()

async def get_deal(deal_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)) as cursor:
            return await cursor.fetchone()

async def update_deal_status(deal_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE deals SET status = ? WHERE id = ?", (status, deal_id))
        await db.commit()
