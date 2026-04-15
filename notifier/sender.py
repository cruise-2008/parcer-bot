from aiogram import Bot
from db.models import Listing, Search

async def notify(bot: Bot, search: Search, listing: Listing):
    price_text = f"{listing.price} €" if listing.price else "Цена не указана"
    location_text = f"📍 {listing.location}" if listing.location else ""

    text = (
        f"🔔 <b>Новое объявление</b>\n\n"
        f"🔍 Поиск: <b>{search.keyword}</b>\n"
        f"📦 {listing.title}\n"
        f"💰 {price_text}\n"
        f"{location_text}\n"
        f"🌐 {listing.platform.capitalize()}\n\n"
        f"🔗 <a href='{listing.url}'>Открыть объявление</a>"
    )

    try:
        if listing.image_url:
            await bot.send_photo(
                chat_id=search.user_id,
                photo=listing.image_url,
                caption=text,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=search.user_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")
