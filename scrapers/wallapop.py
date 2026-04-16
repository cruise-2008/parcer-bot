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
        items = soup.select("[class*='ItemCardGrid']")
        print(f"Wallapop items: {len(items)}")
        if items:
            print(f"Wallapop first item: {items[0].get('class')}")
            print(f"Wallapop first item html: {str(items[0])[:300]}")

        results = []
        for item in items:
            try:
                link_el = item.select_one("a")
                title_el = item.select_one("[class*='title']")
                price_el = item.select_one("[class*='price']")
                image_el = item.select_one("img")

                if not link_el:
                    continue

                href = link_el.get("href", "")
                url = "https://es.wallapop.com" + href if href.startswith("/") else href
                external_id = url.split("/")[-1]
                title = title_el.text.strip() if title_el else ""
                price_text = price_el.text.strip().replace("€", "").replace(".", "").replace(",", "").strip() if price_el else None
                price = int(price_text) if price_text and price_text.isdigit() else None
                image_url = image_el.get("src") if image_el else None

                if not external_id or not title:
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
