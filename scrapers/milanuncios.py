import httpx
from bs4 import BeautifulSoup
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
from antidetect.stealth import get_headers, random_delay

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

        async with httpx.AsyncClient(headers=get_headers(), timeout=15) as client:
            response = await client.get(self.BASE_URL, params=params)

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for item in soup.select("article.ma-AdCard"):
            try:
                external_id = item.get("data-adid", "")
                title_el = item.select_one(".ma-AdCard-title")
                price_el = item.select_one(".ma-AdPrice-value")
                link_el = item.select_one("a.ma-AdCard-titleLink")
                image_el = item.select_one("img.ma-AdCard-photo")
                location_el = item.select_one(".ma-AdCard-location")

                title = title_el.text.strip() if title_el else ""
                price_text = price_el.text.strip().replace(".", "").replace("€", "").strip() if price_el else None
                price = int(price_text) if price_text and price_text.isdigit() else None
                url = "https://www.milanuncios.com" + link_el["href"] if link_el else ""
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
            except Exception:
                continue

        return results
