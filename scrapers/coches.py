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
            await page.wait_for_timeout(4000)
            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        print(f"Coches HTML length: {len(html)}")

        all_articles = soup.find_all("article")
        print(f"Coches all articles: {len(all_articles)}")
        if all_articles:
            for a in all_articles[:3]:
                print(f"Coches article class: {a.get('class')}")

        all_cards = soup.select("[class*='Card']")
        print(f"Coches Card elements: {len(all_cards)}")
        if all_cards:
            print(f"Coches first Card class: {all_cards[0].get('class')}")

        all_items = soup.select("[class*='item']")
        print(f"Coches item elements: {len(all_items)}")
        if all_items:
            print(f"Coches first item class: {all_items[0].get('class')}")

        return []
