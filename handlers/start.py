import os
from aiogram import Router, types
from aiogram.filters import CommandStart
from database import Database
from models import User
from keyboards import get_main_menu

router = Router()

WELCOME_TEXT = (
    "👋 <b>Рад приветствовать вас в типографии «Поликрафт»!</b>\n\n"
    "🤖 <b>Я — ваш цифровой помощник.</b>\n"
    "Моя задача — сэкономить ваше время. Я расскажу о требованиях к макетам, подскажу адрес офиса и свяжу с менеджером, если у вас сложный вопрос.\n\n"
    "🏭 <b>О нас:</b>\n"
    "Мы — типография полного цикла в Минске. За нашими плечами <b>30 лет опыта</b>, "
    "тысячи сданных тиражей и репутация партнера, который держит слово.\n\n"
    "<b>Почему нам доверяют:</b>\n"
    "🚀 <b>Надежность:</b> Умеем работать в режиме «нужно вчера».\n"
    "💎 <b>Сложные задачи:</b> Вырубка, тиснение, конгрев, нестандартные конструкции, "
    "а также уникальная технология скрепления книжных и журнальных блоков <b>PUR-клеем</b>!\n"
    "🌍 <b>География:</b> Производство в Минске, доставка — в любую точку Беларуси.\n\n"
    "Чем я могу помочь вам прямо сейчас?\n"
    "👇 <i>Выберите нужный пункт в меню:</i>"
)


async def check_is_admin(user_id: int, db: Database) -> bool:
    admin_ids = [x.strip() for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
    if str(user_id) in admin_ids:
        return True
    user = await db.get_user(user_id)
    return user is not None and user.role in ("manager", "admin")


@router.message(CommandStart())
async def cmd_start(message: types.Message, db: Database):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    user = User(
        id=user_id,
        username=username,
        full_name=full_name,
        role="client"
    )
    
    await db.upsert_user(user)

    is_admin = await check_is_admin(user_id, db)
    await message.answer(WELCOME_TEXT, reply_markup=get_main_menu(is_admin=is_admin))
