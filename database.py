import aiosqlite
import json
from datetime import datetime
from typing import List, Optional
from models import User, Order

class Database:
    def __init__(self, db_path: str = "polycraft.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    phone TEXT,
                    role TEXT DEFAULT 'client',
                    created_at TIMESTAMP
                )
            """)
            # Таблица заказов
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    category TEXT,
                    params TEXT,
                    description TEXT,
                    files TEXT,
                    status TEXT DEFAULT 'pending_calculation',
                    offered_price REAL DEFAULT 0.0,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            # Таблица акций
            await db.execute("""
                CREATE TABLE IF NOT EXISTS promotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            await db.commit()

    async def close(self):
        pass

    async def get_user(self, user_id: int) -> Optional[User]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    created_at = row['created_at']
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)
                    
                    return User(
                        id=row['id'], 
                        username=row['username'], 
                        full_name=row['full_name'], 
                        phone=row['phone'], 
                        role=row['role'], 
                        created_at=created_at
                    )
                return None

    async def upsert_user(self, user: User):
        async with aiosqlite.connect(self.db_path) as db:
            # Превращаем datetime в строку для SQLite, если нужно
            created_at_str = user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at
            
            await db.execute("""
                INSERT INTO users (id, username, full_name, phone, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username=excluded.username,
                    full_name=excluded.full_name,
                    phone=excluded.phone
            """, (user.id, user.username, user.full_name, user.phone, user.role, created_at_str))
            await db.commit()

    async def create_order(self, order: Order):
        async with aiosqlite.connect(self.db_path) as db:
            created_at = order.created_at.isoformat() if isinstance(order.created_at, datetime) else order.created_at
            updated_at = order.updated_at.isoformat() if isinstance(order.updated_at, datetime) else order.updated_at
            
            cursor = await db.execute("""
                INSERT INTO orders (user_id, category, params, description, files, status, offered_price, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.user_id, order.category, json.dumps(order.params), 
                order.description, ",".join(order.files) if order.files else "", 
                order.status, order.offered_price, created_at, updated_at
            ))
            await db.commit()
            return cursor.lastrowid

    async def get_user_orders(self, user_id: int) -> List[Order]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                orders = []
                for row in rows:
                    created_at = row['created_at']
                    updated_at = row['updated_at']
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at)
                    
                    orders.append(Order(
                        id=row['id'],
                        user_id=row['user_id'],
                        category=row['category'],
                        params=json.loads(row['params']),
                        description=row['description'],
                        files=row['files'].split(',') if row['files'] else [],
                        status=row['status'],
                        offered_price=row['offered_price'],
                        created_at=created_at,
                        updated_at=updated_at
                    ))
                return orders

    async def update_order_status(self, order_id: int, status: str, price: Optional[float] = None):
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now().isoformat()
            if price is not None:
                await db.execute(
                    "UPDATE orders SET status = ?, offered_price = ?, updated_at = ? WHERE id = ?",
                    (status, price, now, order_id)
                )
            else:
                await db.execute(
                    "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
                    (status, now, order_id)
                )
            await db.commit()

    async def get_managers(self) -> List[int]:
        """Возвращает список ID всех пользователей с ролью manager или admin."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM users WHERE role IN ('manager', 'admin')") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
