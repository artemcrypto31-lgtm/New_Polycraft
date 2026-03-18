import aiosqlite
import json
import logging
from datetime import datetime
from typing import List, Optional
from models import User, Order

logger = logging.getLogger(__name__)

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
                    org_name TEXT,
                    city TEXT,
                    address TEXT,
                    email TEXT,
                    role TEXT DEFAULT 'client',
                    created_at TIMESTAMP
                )
            """)
            
            # На случай если таблица уже создана без новых полей (миграция)
            columns = [
                ('org_name', 'TEXT'),
                ('city', 'TEXT'),
                ('address', 'TEXT'),
                ('email', 'TEXT')
            ]
            for col_name, col_type in columns:
                try:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                except:
                    pass

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
            for col_name, col_type in [('manager_id', 'INTEGER')]:
                try:
                    await db.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
                except:
                    pass

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
                        org_name=row['org_name'],
                        city=row['city'],
                        address=row['address'],
                        email=row['email'],
                        role=row['role'], 
                        created_at=created_at
                    )
                return None

    async def upsert_user(self, user: User):
        """Создает пользователя или обновляет базовую информацию, не затирая профиль."""
        async with aiosqlite.connect(self.db_path) as db:
            created_at_str = user.created_at.isoformat() if isinstance(user.created_at, datetime) else user.created_at
            
            # Используем COALESCE, чтобы сохранить старые значения, если новые - NULL
            await db.execute("""
                INSERT INTO users (id, username, full_name, phone, org_name, city, address, email, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username = COALESCE(excluded.username, users.username),
                    full_name = COALESCE(excluded.full_name, users.full_name),
                    role = COALESCE(excluded.role, users.role)
            """, (
                user.id, user.username, user.full_name, user.phone, 
                user.org_name, user.city, user.address, user.email, 
                user.role, created_at_str
            ))
            await db.commit()

    async def update_user_profile(self, user_id: int, **kwargs):
        """Обновляет конкретные поля профиля пользователя."""
        if not kwargs:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            keys = [f"{k} = ?" for k in kwargs.keys()]
            query = f"UPDATE users SET {', '.join(keys)} WHERE id = ?"
            values = list(kwargs.values()) + [user_id]
            await db.execute(query, values)
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
            order_id = cursor.lastrowid
            logger.info(f"✅ Заказ #{order_id} создан в БД (категория: {order.category}, тираж: {order.params.get('count', '?')})")
            return order_id

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
                    
                    manager_id = None
                    try:
                        manager_id = row['manager_id']
                    except (IndexError, KeyError):
                        pass

                    orders.append(Order(
                        id=row['id'],
                        user_id=row['user_id'],
                        category=row['category'],
                        params=json.loads(row['params']),
                        description=row['description'],
                        files=row['files'].split(',') if row['files'] else [],
                        status=row['status'],
                        offered_price=row['offered_price'],
                        manager_id=manager_id,
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
            logger.info(f"✅ Заказ #{order_id} обновлён (статус: {status})")

    async def get_order(self, order_id: int) -> Optional[Order]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    created_at = row['created_at']
                    updated_at = row['updated_at']
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at)

                    manager_id = None
                    try:
                        manager_id = row['manager_id']
                    except (IndexError, KeyError):
                        pass

                    return Order(
                        id=row['id'],
                        user_id=row['user_id'],
                        category=row['category'],
                        params=json.loads(row['params']),
                        description=row['description'],
                        files=row['files'].split(',') if row['files'] else [],
                        status=row['status'],
                        offered_price=row['offered_price'],
                        manager_id=manager_id,
                        created_at=created_at,
                        updated_at=updated_at
                    )
                return None

    async def set_order_price(self, order_id: int, price: float, manager_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now().isoformat()
            await db.execute(
                "UPDATE orders SET offered_price = ?, manager_id = ?, status = 'priced', updated_at = ? WHERE id = ?",
                (price, manager_id, now, order_id)
            )
            await db.commit()
            logger.info(f"💰 Заказу #{order_id} установлена цена {price} (менеджер ID: {manager_id})")

    async def get_managers(self) -> List[int]:
        """Возвращает список ID всех пользователей с ролью manager или admin."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT id FROM users WHERE role IN ('manager', 'admin')") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def get_all_orders(self, status: Optional[str] = None, limit: int = 50) -> List[Order]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                query = "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ?"
                params = (status, limit)
            else:
                query = "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?"
                params = (limit,)
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                orders = []
                for row in rows:
                    created_at = row['created_at']
                    updated_at = row['updated_at']
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)
                    if isinstance(updated_at, str):
                        updated_at = datetime.fromisoformat(updated_at)
                    manager_id = None
                    try:
                        manager_id = row['manager_id']
                    except (IndexError, KeyError):
                        pass
                    orders.append(Order(
                        id=row['id'],
                        user_id=row['user_id'],
                        category=row['category'],
                        params=json.loads(row['params']),
                        description=row['description'],
                        files=row['files'].split(',') if row['files'] else [],
                        status=row['status'],
                        offered_price=row['offered_price'],
                        manager_id=manager_id,
                        created_at=created_at,
                        updated_at=updated_at
                    ))
                return orders

    async def get_order_stats(self) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            async with db.execute("SELECT status, COUNT(*) FROM orders GROUP BY status") as cursor:
                rows = await cursor.fetchall()
                for row in rows:
                    stats[row[0]] = row[1]
            async with db.execute("SELECT COUNT(*) FROM orders") as cursor:
                row = await cursor.fetchone()
                stats['total'] = row[0]
            return stats

    async def get_all_users(self, limit: int = 50) -> List[User]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,)) as cursor:
                rows = await cursor.fetchall()
                users = []
                for row in rows:
                    created_at = row['created_at']
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at)
                    users.append(User(
                        id=row['id'],
                        username=row['username'],
                        full_name=row['full_name'],
                        phone=row['phone'],
                        org_name=row['org_name'],
                        city=row['city'],
                        address=row['address'],
                        email=row['email'],
                        role=row['role'],
                        created_at=created_at
                    ))
                return users

    async def get_user_stats(self) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                stats['total'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'client'") as cursor:
                stats['clients'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'manager'") as cursor:
                stats['managers'] = (await cursor.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'") as cursor:
                stats['admins'] = (await cursor.fetchone())[0]
            return stats

    async def set_user_role(self, user_id: int, role: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
            await db.commit()
