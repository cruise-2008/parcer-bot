from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from db.database import get_pool
from db.models import Search
from scrapers.milanuncios import MilanunciosScraper
from scrapers.wallapop import WallapopScraper
from scrapers.coches import CochesScraper
from notifier.sender import notify
from config import SEARCH_INTERVAL_MINUTES

scrapers = [
    MilanunciosScraper(),
    WallapopScraper(),
    CochesScraper(),
]

async def run_searches(bot: Bot):
    print("🔄 Запуск поиска...")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM searches WHERE active = TRUE")

    print(f"📋 Активных поисков: {len(rows)}")

    for row in rows:
        search = Search(
            id=row["id"],
            user_id=row["user_id"],
            keyword=row["keyword"],
            price_min=row["price_min"],
            price_max=row["price_max"],
            location=row["location"],
            radius=row["radius"],
            active=row["active"]
        )

        for scraper in scrapers:
            try:
                print(f"🌐 {scraper.__class__.__name__} → {search.keyword}")
                listings = await scraper.fetch(search)
                print(f"✅ Найдено: {len(listings)}")
                for listing in listings:
                    pool = await get_pool()
                    async with pool.acquire() as conn:
                        exists = await conn.fetchval(
                            "SELECT id FROM listings WHERE external_id=$1 AND platform=$2",
                            listing.external_id, listing.platform
                        )
                        if not exists:
                            await conn.execute(
                                """INSERT INTO listings
                                (search_id, external_id, platform, title, price, url, image_url, location)
                                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
                                search.id, listing.external_id, listing.platform,
                                listing.title, listing.price, listing.url,
                                listing.image_url, listing.location
                            )
                            await notify(bot, search, listing)
            except Exception as e:
                print(f"❌ Ошибка {scraper.__class__.__name__}: {e}")

def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_searches,
        "interval",
        minutes=SEARCH_INTERVAL_MINUTES,
        args=[bot]
    )
    scheduler.start()
    return scheduler
