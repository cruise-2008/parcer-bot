import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from db.database import get_pool
from db.models import Search
from scrapers.milanuncios import MilanunciosScraper
from scrapers.wallapop import WallapopScraper
from scrapers.coches import CochesScraper
from notifier.sender import notify
from config import SEARCH_INTERVAL_MINUTES

SCRAPERS = {
    "wallapop": WallapopScraper(),
    "milanuncios": MilanunciosScraper(),
    "coches": CochesScraper(),
}

TRUSTED_SCRAPERS = {"wallapop"}

def price_matches(listing, search):
    if listing.price is None:
        return True
    if search.price_min > 0 and listing.price < search.price_min:
        return False
    if search.price_max < 999999 and listing.price > search.price_max:
        return False
    return True

def keyword_matches(listing, search):
    keywords = search.keyword.lower().split()
    title = listing.title.lower()
    return any(kw in title for kw in keywords)

async def process_scraper(bot, search, platform, scraper):
    try:
        print(f"🌐 {platform} → {search.keyword}")
        listings = await asyncio.wait_for(scraper.fetch(search), timeout=60)
        print(f"📦 Получено: {len(listings)}")

        if platform in TRUSTED_SCRAPERS:
            filtered = [l for l in listings if price_matches(l, search)]
        else:
            filtered = [l for l in listings if price_matches(l, search) and keyword_matches(l, search)]

        print(f"✅ После фильтра: {len(filtered)}")

        for listing in filtered:
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
    except asyncio.TimeoutError:
        print(f"⏱ Timeout: {platform} → {search.keyword}")
    except Exception as e:
        print(f"❌ Ошибка {platform}: {e}")

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

        platforms = row["platforms"].split(",") if row["platforms"] else ["wallapop", "milanuncios", "coches"]

        for platform in platforms:
            scraper = SCRAPERS.get(platform.strip())
            if not scraper:
                continue
            await process_scraper(bot, search, platform, scraper)

    print("✅ Цикл поиска завершён")

def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_searches,
        "interval",
        minutes=SEARCH_INTERVAL_MINUTES,
        args=[bot],
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
    return scheduler
