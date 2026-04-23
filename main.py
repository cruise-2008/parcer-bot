import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from config import BOT_TOKEN
from db.database import init_db
from bot.handlers import router
from bot.car_handlers import router as car_router
from core.scheduler import start_scheduler

reset_router = Router()

@reset_router.message(Command("car"), StateFilter("*"))
async def reset_for_car(message: Message, state: FSMContext):
    await state.clear()
    from bot.car_handlers import cmd_car
    await cmd_car(message, state)

@reset_router.message(Command("search"), StateFilter("*"))
async def reset_for_search(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers import cmd_search
    await cmd_search(message, state)

@reset_router.message(Command("list"), StateFilter("*"))
async def reset_for_list(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers import cmd_list
    await cmd_list(message, state)

@reset_router.message(Command("stop"), StateFilter("*"))
async def reset_for_stop(message: Message, state: FSMContext):
    await state.clear()
    from bot.handlers import cmd_stop
    await cmd_stop(message, state)

@reset_router.message(Command("cancel"), StateFilter("*"))
async def reset_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=ReplyKeyboardRemove())

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(reset_router)
    dp.include_router(router)
    dp.include_router(car_router)

    await init_db()
    start_scheduler(bot)

    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
