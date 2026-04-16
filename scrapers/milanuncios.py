from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
import urllib.parse

class MilanunciosScraper(BaseScraper):

    BASE_URL = "https://www.milanuncios.com/anuncios/"

    async def fetch(self, search: Search) -> List[Listing]:
        params = {
            "titulo": search.keyword,
            "preciomax": search.price_max,
            "preciomin": search.price_min,
        }
        if search.location:
            params["where"] = search.location
            params["radio"] = search.radius

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
        items = soup.select("article.ma-AdCardV2")
        print(f"Milanuncios items: {len(items)}")

        if items:
            print(f"Milanuncios first item html: {str(items[0])[:500]}")

        results = []
        for item in items:
            try:
                link_el = item.select_one("a[href]")
                title_el = item.select_one("[class*='title']")
                if not title_el:
                    title_el = item.select_one("[class*='Title']")
                price_el = item.select_one("[class*='price']")
                if not price_el:
                    price_el = item.select_one("[class*='Price']")
                image_el = item.select_one("img")
                location_el = item.select_one("[class*='location']")
                if not location_el:
                    location_el = item.select_one("[class*='Location']")

                if not link_el:
                    continue

                href = link_el.get("href", "")
                url = "https://www.milanuncios.com" + href if href.startswith("/") else href
                external_id = href.strip("/").split("/")[-1]

                title = title_el.text.strip() if title_el else ""
                price_text = price_el.text.strip().replace(".", "").replace("€", "").replace(",", "").strip() if price_el else None
                price = int(price_text) if price_text and price_text.isdigit() else None
                image_url = image_el.get("src") or image_el.get("data-src") if image_el else None
                location = location_el.text.strip() if location_el else ""

                if not external_id or not url:
                    continue

                results.append(self.build_listing(
                    external_id=external_id,
                    platform="milanuncios",
                    title=title,
                    price=price,
                    url=url,
                    image_url=image_url,
                    location=location
                ))
            except Exception as e:
                print(f"Milanuncios item error: {e}")
                continue

        print(f"Milanuncios results: {len(results)}")
        return results
