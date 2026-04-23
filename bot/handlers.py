import json
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup, default_state
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
            [KeyboardButton(text="✅ Wallapop"), KeyboardButton(text="✅ Milanuncios")],
            [KeyboardButton(text="✅ Coches.net")],
            [KeyboardButton(text="🚀 Готово")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

PLATFORM_KEYS = {
    "✅ Wallapop": "wallapop",
    "✅ Milanuncios": "milanuncios",
    "✅ Coches.net": "coches",
}

def format_search(row):
    try:
        meta = json.loads(row["keyword"])
        if meta.get("type") == "car":
            model = meta.get("model") or "любая модель"
            fuel = meta.get("fuel_label", "")
            return (
                f"🚗 {meta['brand']} {model}\n"
                f"⛽ {fuel}\n"
                f"📅 от {meta.get('year_from', '—')} г.\n"
                f"💰 {row['price_min']} — {row['price_max']} €\n"
                f"🌐 {row['platforms']}"
            )
    except Exception:
        pass
    return (
        f"🔍 {row['keyword']}\n"
        f"💰 {row['price_min']} — {row['price_max']} €\n"
        f"📍 {row['location'] or 'Вся Испания'}\n"
        f"🌐 {row['platforms']}"
    )

@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=ReplyKeyboardRemove())

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Я ищу объявления на Milanuncios, Wallapop и Coches.net\n\n"
        "📌 Команды:\n"
        "/search — поиск товаров\n"
        "/car — поиск автомобилей\n"
        "/list — мои активные поиски\n"
        "/stop — остановить поиск\n"
        "/cancel — отменить текущее действие",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SearchForm.keyword)
    await message.answer("🔍 Введи ключевое слово для поиска:")

@router.message(Command("list"))
async def cmd_list(message: Message, state: FSMContext):
    await state.clear()
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
        text += f"🆔 ID: {row['id']}\n"
        text += format_search(row)
        text += "\n\n"
    text += "Чтобы остановить поиск: /stop"
    await message.answer(text)

@router.message(Command("stop"))
async def cmd_stop(message: Message, state: FSMContext):
    await state.clear()
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
        try:
            meta = json.loads(row["keyword"])
            label = f"🚗 {meta.get('brand', '')} {meta.get('model', '')}"
        except Exception:
            label = row["keyword"]
        text += f"🆔 {row['id']} — {label}\n"
    await state.set_state(StopForm.search_id)
    await message.answer(text)

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
    await state.update_data(location=location, selected_platforms=[])
    await state.set_state(SearchForm.platforms)
    await message.answer(
        "🌐 Выбери площадки (нажимай по одной, затем нажми 🚀 Готово):\n\nПока не выбрано ни одной.",
        reply_markup=platforms_keyboard()
    )

@router.message(SearchForm.platforms)
async def process_platforms(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    selected = data.get("selected_platforms", [])

    if text == "🚀 Готово":
        if not selected:
            await message.answer("Выбери хотя бы одну площадку!")
            return

        platforms_str = ",".join(selected)
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
                platforms_str
            )

        await state.clear()
        names = [k for k, v in PLATFORM_KEYS.items() if v in selected]
        await message.answer(
            f"✅ Поиск создан!\n\n"
            f"🔍 {data['keyword']}\n"
            f"💰 {data['price_min']} — {data['price_max']} €\n"
            f"📍 {data['location'] or 'Вся Испания'}\n"
            f"🌐 {', '.join(names)}\n\n"
            f"Буду присылать новые объявления каждые 10 минут.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    platform = PLATFORM_KEYS.get(text)
    if platform:
        if platform not in selected:
            selected.append(platform)
        else:
            selected.remove(platform)
        await state.update_data(selected_platforms=selected)
        names = [k for k, v in PLATFORM_KEYS.items() if v in selected]
        await message.answer(
            f"🌐 Выбрано: {', '.join(names) if names else 'ничего'}\n\nНажми 🚀 Готово когда закончишь.",
            reply_markup=platforms_keyboard()
        )

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
