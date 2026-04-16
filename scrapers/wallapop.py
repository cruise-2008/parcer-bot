from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
import urllib.parse

class WallapopScraper(BaseScraper):

    BASE_URL = "https://es.wallapop.com/app/search"

    async def fetch(self, search: Search) -> List[Listing]:
        params = {
            "keywords": search.keyword,
            "minPrice": search.price_min,
            "maxPrice": search.price_max,
            "orderBy": "newest",
        }
        url = self.BASE_URL + "?" + urllib.parse.urlencode(params)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-ES",
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(4000)
            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("a[href*='/item/']")
        print(f"Wallapop items: {len(items)}")

        results = []
        for item in items:
            try:
                href = item.get("href", "")
                if not href or "/item/" not in href:
                    continue

                url = "https://es.wallapop.com" + href if href.startswith("/") else href
                external_id = href.split("/item/")[-1].split("?")[0]

                title_el = item.select_one("[class*='title']")
                if not title_el:
                    title_el = item.select_one("[class*='Title']")

                price_el = item.select_one("[class*='price']")
                if not price_el:
                    price_el = item.select_one("[class*='Price']")

                image_el = item.select_one("img")

                title = title_el.text.strip() if title_el else ""
                if not title or len(title) < 3:
                    continue

                price_text = price_el.text.strip().replace("€", "").replace(".", "").replace(",", "").strip() if price_el else None
                price = int(price_text) if price_text and price_text.isdigit() else None
                image_url = image_el.get("src") if image_el else None

                if not external_id:
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
            except Exception as e:
                print(f"Wallapop item error: {e}")
                continue

        print(f"Wallapop results: {len(results)}")
        return results
