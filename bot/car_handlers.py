import json
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

def brand_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔀 Любая марка")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

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
    "🔋 Гибрид": {"wallapop": "hybride", "coches": "hibrido", "label": "Гибрид"},
    "⚡ Электро": {"wallapop": "electric", "coches": "electrico", "label": "Электро"},
    "⛽ Бензин": {"wallapop": "gasoline", "coches": "gasolina", "label": "Бензин"},
    "🛢 Дизель": {"wallapop": "diesel", "coches": "diesel", "label": "Дизель"},
    "🔀 Любой тип": {"wallapop": "", "coches": "", "label": "Любой тип"},
}

PLATFORM_MAP = {
    "🚗 Coches.net": "coches",
    "🛍 Wallapop": "wallapop",
    "🚗 Coches.net + 🛍 Wallapop": "coches,wallapop",
}

@router.message(Command("car"))
async def cmd_car(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CarForm.brand)
    await message.answer(
        "🚗 Какую марку автомобиля ищешь?\n\nПример: Toyota, BMW, Ford\nИли нажми кнопку если марка не важна:",
        reply_markup=brand_keyboard()
    )

@router.message(CarForm.brand)
async def process_brand(message: Message, state: FSMContext):
    text = message.text.strip()

    if text == "🔀 Любая марка":
        await state.update_data(brand="")
        await state.set_state(CarForm.model)
        await message.answer(
            "✅ Любая марка\n\n📝 Модель? Напиши или <b>0</b> чтобы пропустить:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return

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
            "Марка не найдена 🤔\n\nПопробуй ещё раз или нажми кнопку:",
            reply_markup=brand_keyboard()
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
            "Введи марку заново или нажми кнопку:",
            reply_markup=brand_keyboard()
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
    fuel = FUEL_MAP.get(message.text.strip(), {"wallapop": "", "coches": "", "label": "Любой тип"})
    await state.update_data(fuel=fuel, fuel_label=fuel["label"])
    await state.set_state(CarForm.year_from)
    await message.answer(
        "📅 С какого года искать?\n\nПример: 2010\nНапиши <b>0</b> если год не важен:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(CarForm.year_from)
async def process_year_from(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "0":
        await state.update_data(year_from=1990)
    elif not text.isdigit() or int(text) < 1990 or int(text) > 2025:
        await message.answer("Введи корректный год, например: 2010 или 0:")
        return
    else:
        await state.update_data(year_from=int(text))
    await state.set_state(CarForm.max_km)
    await message.answer(
        "🛣 Максимальный пробег (км)?\n\nПример: 150000\nНапиши <b>0</b> если без ограничения:",
        parse_mode="HTML"
    )

@router.message(CarForm.max_km)
async def process_max_km(message: Message, state: FSMContext):
    text = message.text.strip()
    if text == "0":
        await state.update_data(max_km=999999)
    elif not text.isdigit():
        await message.answer("Введи число, например: 150000 или 0:")
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
    fuel = data.get("fuel", {"wallapop": "", "coches": "", "label": "Любой тип"})

    meta = json.dumps({
        "type": "car",
        "brand": data.get("brand", ""),
        "model": data.get("model", ""),
        "fuel_wallapop": fuel.get("wallapop", ""),
        "fuel_coches": fuel.get("coches", ""),
        "fuel_label": fuel.get("label", "Любой тип"),
        "year_from": data.get("year_from", 1990),
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
    brand_text = data.get("brand") or "Любая"
    model_text = data.get("model") or "Любая"
    max_km = data.get("max_km", 999999)
    km_text = f"{max_km:,} км".replace(",", " ") if max_km < 999999 else "Без ограничения"
    year = data.get("year_from", 1990)
    year_text = str(year) if year > 1990 else "Любой"

    await message.answer(
        f"✅ Поиск авто создан!\n\n"
        f"🚗 Марка: {brand_text}\n"
        f"📋 Модель: {model_text}\n"
        f"⛽ Топливо: {fuel.get('label', 'Любой тип')}\n"
        f"📅 Год от: {year_text}\n"
        f"🛣 Пробег до: {km_text}\n"
        f"💰 Цена: {data['price_min']} — {data['price_max']} €\n"
        f"🌐 {text}\n\n"
        f"Буду присылать новые объявления каждые 10 минут.",
        reply_markup=ReplyKeyboardRemove()
    )
