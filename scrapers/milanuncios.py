import httpx
from bs4 import BeautifulSoup
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
from antidetect.stealth import random_delay
from config import SCRAPERAPI_KEY
import urllib.parse

class MilanunciosScraper(BaseScraper):

    BASE_URL = "https://www.milanuncios.com/anuncios/"

    async def fetch(self, search: Search) -> List[Listing]:
        await random_delay()

        params = {
            "titulo": search.keyword,
            "preciomax": search.price_max,
            "preciomin": search.price_min,
        }
        if search.location:
            params["where"] = search.location
            params["radio"] = search.radius

        target_url = self.BASE_URL + "?" + urllib.parse.urlencode(params)
        scraper_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={urllib.parse.quote(target_url)}"

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(scraper_url)

        print(f"Milanuncios status: {response.status_code}")

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        all_articles = soup.find_all("article")
        print(f"Milanuncios all articles: {len(all_articles)}")
        if all_articles:
            print(f"Milanuncios first article classes: {all_articles[0].get('class')}")

        all_adcards = soup.select("[class*='AdCard']")
        print(f"Milanuncios AdCard elements: {len(all_adcards)}")
        if all_adcards:
            print(f"Milanuncios first AdCard class: {all_adcards[0].get('class')}")

        return []
