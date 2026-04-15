import httpx
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
from antidetect.stealth import get_headers, random_delay

class WallapopScraper(BaseScraper):

    BASE_URL = "https://api.wallapop.com/api/v3/search"

    async def fetch(self, search: Search) -> List[Listing]:
        await random_delay()

        params = {
            "keywords": search.keyword,
            "min_sale_price": search.price_min,
            "max_sale_price": search.price_max,
            "order_by": "newest",
            "start": 0,
            "step": 20,
        }
        if search.location:
            params["location"] = search.location
            params["distance"] = search.radius * 1000

        headers = get_headers()
        headers["Accept"] = "application/json"

        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            response = await client.get(self.BASE_URL, params=params)

        if response.status_code != 200:
            return []

        data = response.json()
        items = data.get("search_objects", [])
        results = []

        for item in items:
            try:
                external_id = str(item.get("id", ""))
                title = item.get("title", "")
                price = int(float(item.get("sale_price", 0)))
                url = f"https://es.wallapop.com/item/{item.get('web_slug', '')}"
                images = item.get("images", [])
                image_url = images[0].get("original") if images else None
                location = item.get("location", {}).get("city", "")

                if not external_id:
                    continue

                results.append(self.build_listing(
                    external_id=external_id,
                    platform="wallapop",
                    title=title,
                    price=price,
                    url=url,
                    image_url=image_url,
                    location=location
                ))
            except Exception:
                continue

        return results
