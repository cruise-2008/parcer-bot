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
        print(f"Milanuncios HTML length: {len(html)}")

        all_articles = soup.find_all("article")
        print(f"Milanuncios all articles: {len(all_articles)}")
        if all_articles:
            for a in all_articles[:3]:
                print(f"Milanuncios article class: {a.get('class')}")

        all_cards = soup.select("[class*='Ad']")
        print(f"Milanuncios Ad elements: {len(all_cards)}")
        if all_cards:
            print(f"Milanuncios first Ad class: {all_cards[0].get('class')}")

        all_li = soup.find_all("li")
        print(f"Milanuncios li elements: {len(all_li)}")
        if all_li:
            for li in all_li[:3]:
                print(f"Milanuncios li class: {li.get('class')}")

        return []
