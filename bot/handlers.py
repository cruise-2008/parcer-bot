from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.database import get_pool

router = Router()

class SearchForm(StatesGroup):
    keyword = State()
    price_min = State()
    price_max = State()
    location = State()
    platforms = State()

class StopForm(StatesGroup):
    search_id = State()

def platforms_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Wallapop")],
            [KeyboardButton(text="Milanuncios")],
            [KeyboardButton(text="Coches.net")],
            [KeyboardButton(text="Wallapop + Milanuncios")],
            [KeyboardButton(text="Wallapop + Coches.net")],
            [KeyboardButton(text="Milanuncios + Coches.net")],
            [KeyboardButton(text="Все площадки")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

PLATFORM_MAP = {
    "Wallapop": "wallapop",
    "Milanuncios": "milanuncios",
    "Coches.net": "coches",
    "Wallapop + Milanuncios": "wallapop,milanuncios",
    "Wallapop + Coches.net": "wallapop,coches",
    "Milanuncios + Coches.net": "milanuncios,coches",
    "Все площадки": "wallapop,milanuncios,coches",
}

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я ищу объявления на Milanuncios, Wallapop и Coches.net\n\n"
        "📌 Команды:\n"
        "/search — создать новый поиск\n"
        "/list — мои активные поиски\n"
        "/stop — остановить поиск"
    )

@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await state.set_state(SearchForm.keyword)
    await message.answer("🔍 Введи ключевое слово для поиска:")

@router.message(SearchForm.keyword)
async def process_keyword(message: Message, state: FSMContext):
    await state.update_data(keyword=message.text.strip())
    await state.set_state(SearchForm.price_min)
    await message.answer("💰 Минимальная цена (€)? Напиши 0 если без ограничений:")

@router.message(SearchForm.price_min)
async def process_price_min(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Введи число:")
        return
    await state.update_data(price_min=int(text))
    await state.set_state(SearchForm.price_max)
    await message.answer("💰 Максимальная цена (€)? Напиши 999999 если без ограничений:")

@router.message(SearchForm.price_max)
async def process_price_max(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Введи число:")
        return
    await state.update_data(price_max=int(text))
    await state.set_state(SearchForm.location)
    await message.answer("📍 Город или регион? Напиши 0 если без ограничений:")

@router.message(SearchForm.location)
async def process_location(message: Message, state: FSMContext):
    location = message.text.strip()
    if location == "0":
        location = ""
    await state.update_data(location=location)
    await state.set_state(SearchForm.platforms)
    await message.answer(
        "🌐 Выбери площадки для поиска:",
        reply_markup=platforms_keyboard()
    )

@router.message(SearchForm.platforms)
async def process_platforms(message: Message, state: FSMContext):
    text = message.text.strip()
    platforms = PLATFORM_MAP.get(text, "wallapop,milanuncios,coches")
    data = await state.get_data()

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO searches (user_id, keyword, price_min, price_max, location, platforms)
            VALUES ($1, $2, $3, $4, $5, $6)""",
            message.from_user.id,
            data["keyword"],
            data["price_min"],
            data["price_max"],
            data["location"],
            platforms
        )

    await state.clear()
    await message.answer(
        f"✅ Поиск создан!\n\n"
        f"🔍 {data['keyword']}\n"
        f"💰 {data['price_min']} — {data['price_max']} €\n"
        f"📍 {data['location'] or 'Вся Испания'}\n"
        f"🌐 {text}\n\n"
        f"Буду присылать новые объявления каждые 10 минут.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(Command("list"))
async def cmd_list(message: Message):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM searches WHERE user_id=$1 AND active=TRUE",
            message.from_user.id
        )

    if not rows:
        await message.answer("У тебя нет активных поисков. /search — создать новый.")
        return

    text = "📋 Твои активные поиски:\n\n"
    for row in rows:
        text += (
            f"🆔 ID: {row['id']}\n"
            f"🔍 {row['keyword']}\n"
            f"💰 {row['price_min']} — {row['price_max']} €\n"
            f"📍 {row['location'] or 'Вся Испания'}\n"
            f"🌐 {row['platforms']}\n\n"
        )
    text += "Чтобы остановить поиск: /stop"
    await message.answer(text)

@router.message(Command("stop"))
async def cmd_stop(message: Message, state: FSMContext):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, keyword FROM searches WHERE user_id=$1 AND active=TRUE",
            message.from_user.id
        )

    if not rows:
        await message.answer("Нет активных поисков.")
        return

    text = "Какой поиск остановить? Напиши ID:\n\n"
    for row in rows:
        text += f"🆔 {row['id']} — {row['keyword']}\n"
    await state.set_state(StopForm.search_id)
    await message.answer(text)

@router.message(StopForm.search_id)
async def process_stop_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Напиши только цифру — ID поиска:")
        return
    search_id = int(text)
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE searches SET active=FALSE WHERE id=$1 AND user_id=$2",
            search_id, message.from_user.id
        )
    await state.clear()
    if result == "UPDATE 1":
        await message.answer(f"✅ Поиск {search_id} остановлен.")
    else:
        await message.answer("Поиск не найден.")
