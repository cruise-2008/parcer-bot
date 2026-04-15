import httpx
from bs4 import BeautifulSoup
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
from antidetect.stealth import get_headers, random_delay

class CochesScraper(BaseScraper):

    BASE_URL = "https://www.coches.net/segunda-mano/"

    async def fetch(self, search: Search) -> List[Listing]:
        await random_delay()

        params = {
            "txt": search.keyword,
            "precioMaximo": search.price_max,
            "precioMinimo": search.price_min,
        }

        async with httpx.AsyncClient(headers=get_headers(), timeout=15) as client:
            response = await client.get(self.BASE_URL, params=params)

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        for item in soup.select("article.mt-CardAd"):
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

        return results
