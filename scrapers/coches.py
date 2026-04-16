from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
import urllib.parse

class CochesScraper(BaseScraper):

    BASE_URL = "https://www.coches.net/segunda-mano/"

    async def fetch(self, search: Search) -> List[Listing]:
        params = {
            "txt": search.keyword,
            "precioMaximo": search.price_max,
            "precioMinimo": search.price_min,
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
            await page.wait_for_timeout(3000)
            html = await page.content()
            await browser.close()

        print(f"Coches HTML length: {len(html)}")
        soup = BeautifulSoup(html, "html.parser")

        items = soup.select("article.mt-CardAd")
        print(f"Coches items: {len(items)}")
        if not items:
            all_articles = soup.find_all("article")
            print(f"Coches all articles: {len(all_articles)}")
            if all_articles:
                print(f"Coches first article class: {all_articles[0].get('class')}")

        results = []
        for item in items:
            try:
                link_el = item.select_one("a.mt-CardAd-link")
                title_el = item.select_one(".mt-CardAd-title")
                price_el = item.select_one(".mt-CardAd-price")
                image_el = item.select_one("img.mt-CardAd-photo")
                location_el = item.select_one(".mt-CardAd-location")

                if not link_el:
                    continue

                url = link_el.get("href", "")
                if url.startswith("/"):
                    url = "https://www.coches.net" + url

                external_id = url.split("/")[-2] if url else ""
                title = title_el.text.strip() if title_el else ""
                price_text = price_el.text.strip().replace(".", "").replace("€", "").strip() if price_el else None
                price = int(price_text) if price_text and price_text.isdigit() else None
                image_url = image_el.get("src") or image_el.get("data-src") if image_el else None
                location = location_el.text.strip() if location_el else ""

                if not external_id:
                    continue

                results.append(self.build_listing(
                    external_id=external_id,
                    platform="coches",
                    title=title,
                    price=price,
                    url=url,
                    image_url=image_url,
                    location=location
                ))
            except Exception:
                continue

        print(f"Coches results: {len(results)}")
        return results
