import asyncio
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from db.database import get_pool
from db.models import Search
from scrapers.milanuncios import MilanunciosScraper
from scrapers.wallapop import WallapopScraper
from scrapers.coches import CochesScraper
from notifier.sender import notify

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

def is_car_search(search):
    try:
        meta = json.loads(search.keyword)
        return meta.get("type") == "car"
    except Exception:
        return False

async def process_scraper(bot, search, platform, scraper):
    try:
        print(f"🌐 {platform} → {search.keyword[:50]}")
        listings = await asyncio.wait_for(scraper.fetch(search), timeout=60)
        print(f"📦 Получено: {len(listings)}")

        car_search = is_car_search(search)
        if car_search or platform in TRUSTED_SCRAPERS:
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
        print(f"⏱ Timeout: {platform} → {search.keyword[:30]}")
    except Exception as e:
        print(f"❌ Ошибка {platform}: {e}")

async def run_search_by_id(bot: Bot, search_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM searches WHERE id=$1 AND active=TRUE", search_id
        )
    if not row:
        return

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

    platforms = row["platforms"].split(",") if row["platforms"] else ["wallapop"]
    for platform in platforms:
        scraper = SCRAPERS.get(platform.strip())
        if scraper:
            await process_scraper(bot, search, platform, scraper)

async def schedule_all_searches(bot: Bot, scheduler: AsyncIOScheduler):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, interval_minutes FROM searches WHERE active=TRUE")

    added = 0
    for row in rows:
        job_id = f"search_{row['id']}"
        interval = row["interval_minutes"] or 60
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                run_search_by_id,
                "interval",
                minutes=interval,
                args=[bot, row["id"]],
                id=job_id,
                max_instances=1,
                coalesce=True
            )
            added += 1

    if added > 0:
        print(f"📅 Добавлено новых поисков: {added}")

def start_scheduler(bot: Bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        schedule_all_searches,
        "interval",
        minutes=1,
        args=[bot, scheduler],
        id="meta_scheduler",
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
    return scheduler
