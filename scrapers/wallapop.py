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
            "filters_source": "search_box",
            "order_by": "newest",
            "start": 0,
            "step": 20,
            "language": "es_ES",
        }

        if search.price_min > 0:
            params["min_sale_price"] = search.price_min
        if search.price_max < 999999:
            params["max_sale_price"] = search.price_max

        headers = get_headers()
        headers["Accept"] = "application/json, text/plain, */*"
        headers["Origin"] = "https://es.wallapop.com"
        headers["Referer"] = "https://es.wallapop.com/"
        headers["X-AppVersion"] = "84600"
        headers["DeviceOS"] = "0"

        async with httpx.AsyncClient(headers=headers, timeout=15) as client:
            response = await client.get(self.BASE_URL, params=params)

        print(f"Wallapop status: {response.status_code}")
        print(f"Wallapop response: {response.text[:300]}")

        if response.status_code != 200:
            return []

        data = response.json()
        items = data.get("search_objects", [])
        print(f"Wallapop items: {len(items)}")
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
            except Exception as e:
                print(f"Wallapop item error: {e}")
                continue

        return results
