from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from db.database import get_pool
from bot.car_brands import find_brand

router = Router()

class CarForm(StatesGroup):
    brand = State()
    brand_confirm = State()
    model = State()
    fuel = State()
    year_from = State()
    max_km = State()
    price_min = State()
    price_max = State()
    platforms = State()

def fuel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔋 Гибрид"), KeyboardButton(text="⚡ Электро")],
            [KeyboardButton(text="⛽ Бензин"), KeyboardButton(text="🛢 Дизель")],
            [KeyboardButton(text="🔀 Любой тип")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def confirm_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет, введу снова")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def platforms_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚗 Coches.net")],
            [KeyboardButton(text="🛍 Wallapop")],
            [KeyboardButton(text="🚗 Coches.net + 🛍 Wallapop")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

FUEL_MAP = {
    "🔋 Гибрид": {"wallapop": "hybride", "coches": "hibrido"},
    "⚡ Электро": {"wallapop": "electric", "coches": "electrico"},
    "⛽ Бензин": {"wallapop": "gasoline", "coches": "gasolina"},
    "🛢 Дизель": {"wallapop": "diesel", "coches": "diesel"},
    "🔀 Любой тип": {"wallapop": "", "coches": ""},
}

PLATFORM_MAP = {
    "🚗 Coches.net": "coches",
    "🛍 Wallapop": "wallapop",
    "🚗 Coches.net + 🛍 Wallapop": "coches,wallapop",
}

@router.message(Command("car"))
async def cmd_car(message: Message, state: FSMContext):
    await state.set_state(CarForm.brand)
    await message.answer("🚗 Какую марку автомобиля ищешь?\n\nПример: Toyota, BMW, Ford")

@router.message(CarForm.brand)
async def process_brand(message: Message, state: FSMContext):
    text = message.text.strip()
    brand, score = find_brand(text)

    if score == 1.0:
        await state.update_data(brand=brand)
        await state.set_state(CarForm.model)
        await message.answer(
            f"✅ Марка: <b>{brand}</b>\n\n"
            f"📝 Какую модель ищешь?\n"
            f"Если модель не важна — напиши <b>0</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
    elif brand:
        await state.update_data(suggested_brand=brand)
        await state.set_state(CarForm.brand_confirm)
        await message.answer(
            f"Вы имели в виду <b>{brand}</b>?",
            parse_mode="HTML",
            reply_markup=confirm_keyboard()
        )
    else:
        await message.answer(
            "Марка не найдена 🤔\n\nПопробуй ещё раз, например:\nToyota, BMW, Mercedes-Benz, Kia"
        )

@router.message(CarForm.brand_confirm)
async def process_brand_confirm(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "✅ Да":
        data = await state.get_data()
        await state.update_data(brand=data["suggested_brand"])
        await state.set_state(CarForm.model)
        await message.answer(
            f"✅ Марка: <b>{data['suggested_brand']}</b>\n\n"
            f"📝 Какую модель ищешь?\n"
            f"Если модель не важна — напиши <b>0</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await state.set_state(CarForm.brand)
        await message.answer(
            "Введи марку заново, например: Toyota, BMW, Ford",
            reply_markup=ReplyKeyboardRemove()
        )

@router.message(CarForm.model)
async def process_model(message: Message, state: FSMContext):
    model = message.text.strip()
    if model == "0":
        model = ""
        await message.answer("Любая модель — понял ✅")
    else:
        await message.answer(f"Модель: <b>{model}</b> ✅", parse_mode="HTML")
    await state.update_data(model=model)
    await state.set_state(CarForm.fuel)
    await message.answer("⛽ Выбери тип топлива:", reply_markup=fuel_keyboard())

@router.message(CarForm.fuel)
async def process_fuel(message: Message, state: FSMContext):
    fuel = FUEL_MAP.get(message.text.strip(), {"wallapop": "", "coches": ""})
    await state.update_data(fuel=fuel, fuel_label=message.text.strip())
    await state.set_state(CarForm.year_from)
    await message.answer(
        "📅 С какого года искать?\n\nПример: 2010",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(CarForm.year_from)
async def process_year_from(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit() or int(text) < 1990 or int(text) > 2025:
        await message.answer("Введи корректный год, например: 2010")
        return
    await state.update_data(year_from=int(text))
    await state.set_state(CarForm.max_km)
    await message.answer(
        "🛣 Максимальный пробег (км)?\n\nПример: 150000\nЕсли без ограничения — напиши <b>0</b>",
        parse_mode="HTML"
    )

@router.message(CarForm.max_km)
async def process_max_km(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "0":
        await state.update_data(max_km=999999)
    elif not text.isdigit():
        await message.answer("Введи число, например: 150000")
        return
    else:
        await state.update_data(max_km=int(text))
    await state.set_state(CarForm.price_min)
    await message.answer("💰 Минимальная цена (€)?\n\nПример: 2000")

@router.message(CarForm.price_min)
async def process_price_min(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Введи число, например: 2000")
        return
    await state.update_data(price_min=int(text))
    await state.set_state(CarForm.price_max)
    await message.answer("💰 Максимальная цена (€)?\n\nПример: 10000")

@router.message(CarForm.price_max)
async def process_price_max(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Введи число, например: 10000")
        return
    await state.update_data(price_max=int(text))
    await state.set_state(CarForm.platforms)
    await message.answer("🌐 Где искать?", reply_markup=platforms_keyboard())

@router.message(CarForm.platforms)
async def process_platforms(message: Message, state: FSMContext):
    text = message.text.strip()
    platforms = PLATFORM_MAP.get(text, "coches,wallapop")
    data = await state.get_data()

    fuel = data.get("fuel", {"wallapop": "", "coches": ""})
    keyword = f"{data['brand']}"
    if data.get("model"):
        keyword += f" {data['model']}"
    if fuel.get("coches"):
        keyword += f" {fuel['coches']}"

    import json
    meta = json.dumps({
        "type": "car",
        "brand": data["brand"],
        "model": data.get("model", ""),
        "fuel_wallapop": fuel.get("wallapop", ""),
        "fuel_coches": fuel.get("coches", ""),
        "year_from": data.get("year_from", 2000),
        "max_km": data.get("max_km", 999999),
    })

    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO searches
            (user_id, keyword, price_min, price_max, location, platforms)
            VALUES ($1, $2, $3, $4, $5, $6)""",
            message.from_user.id,
            meta,
            data["price_min"],
            data["price_max"],
            "",
            platforms
        )

    await state.clear()
    model_text = data.get("model") or "Любая"
    fuel_label = data.get("fuel_label", "Любой тип")
    max_km = data.get("max_km", 999999)
    km_text = f"{max_km:,} км" if max_km < 999999 else "Без ограничения"

    await message.answer(
        f"✅ Поиск авто создан!\n\n"
        f"🚗 Марка: {data['brand']}\n"
        f"📋 Модель: {model_text}\n"
        f"⛽ Топливо: {fuel_label}\n"
        f"📅 Год от: {data.get('year_from')}\n"
        f"🛣 Пробег до: {km_text}\n"
        f"💰 Цена: {data['price_min']} — {data['price_max']} €\n"
        f"🌐 {text}\n\n"
        f"Буду присылать новые объявления каждые 10 минут.",
        reply_markup=ReplyKeyboardRemove()
    )
