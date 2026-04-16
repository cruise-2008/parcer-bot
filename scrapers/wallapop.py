import httpx
from bs4 import BeautifulSoup
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
from antidetect.stealth import random_delay
from config import SCRAPERAPI_KEY

class WallapopScraper(BaseScraper):

    BASE_URL = "https://es.wallapop.com/app/search"

    async def fetch(self, search: Search) -> List[Listing]:
        await random_delay()

        params = f"keywords={search.keyword}&minPrice={search.price_min}&maxPrice={search.price_max}&orderBy=newest"
        scraper_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={self.BASE_URL}?{params}&render=true"

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(scraper_url)

        print(f"Wallapop status: {response.status_code}")

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("a.ItemCardList__item")
        print(f"Wallapop items found: {len(items)}")

        results = []
        for item in items:
            try:
                url = "https://es.wallapop.com" + item.get("href", "")
                external_id = url.split("/")[-1]
                title_el = item.select_one(".ItemCard__title")
                price_el = item.select_one(".ItemCard__price")
                image_el = item.select_one("img")

                title = title_el.text.strip() if title_el else ""
                price_text = price_el.text.strip().replace("€", "").replace(".", "").strip() if price_el else None
                price = int(price_text) if price_text and price_text.isdigit() else None
                image_url = image_el.get("src") if image_el else None

                if not external_id or not url:
                    continue

                results.append(self.build_listing(
                    external_id=external_id,
                    platform="wallapop",
                    title=title,
                    price=price,
                    url=url,
                    image_url=image_url,
                    location=""
                ))
            except Exception:
                continue

        return results
