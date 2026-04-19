from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List
from db.models import Listing, Search
from scrapers.base import BaseScraper
from bot.car_makes import COCHES_MAKES, COCHES_FUEL
import urllib.parse

class CochesScraper(BaseScraper):

    BASE_URL = "https://www.coches.net/segunda-mano/"

    async def fetch(self, search: Search) -> List[Listing]:
        params = {}

        keywords = search.keyword.lower().split()
        make_id = None
        fuel_id = None

        for kw in keywords:
            for make_name, make_code in COCHES_MAKES.items():
                if kw in make_name.lower() or make_name.lower() in kw:
                    make_id = make_code
                    break
            for fuel_name, fuel_code in COCHES_FUEL.items():
                if fuel_name and kw in fuel_name.lower():
                    fuel_id = fuel_code
                    break

        if not make_id:
            print(f"Coches: марка не найдена для '{search.keyword}' — пропускаем")
            return []

        params["MakeIds[0]"] = make_id
        if fuel_id:
            params["Fueltype2List"] = fuel_id
        if search.price_min > 0:
            params["MinPrice"] = search.price_min
        if search.price_max < 999999:
            params["MaxPrice"] = search.price_max

        url = self.BASE_URL + "?" + urllib.parse.urlencode(params)
        print(f"Coches URL: {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-ES",
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            try:
                await page.wait_for_selector("div.mt-CardAd", timeout=10000)
            except Exception:
                print("Coches: карточки не появились — ждём дольше")
                await page.wait_for_timeout(5000)

            html = await page.content()
            await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        items = soup.select("div.mt-CardAd")
        print(f"Coches items: {len(items)}")

        if not items:
            all_divs = soup.select("[class*='Card']")
            print(f"Coches Card divs: {len(all_divs)}")
            if all_divs:
                print(f"Coches first Card class: {all_divs[0].get('class')}")

        results = []
        for item in items:
            try:
                link_el = item.select_one("a[href]")
                title_el = item.select_one("h2")
                if not title_el:
                    title_el = item.select_one("[class*='Title']")
                price_el = item.select_one("[class*='Price']")
                if not price_el:
                    price_el = item.select_one("[class*='price']")
                image_el = item.select_one("img")
                location_el = item.select_one("[class*='Location']")
                if not location_el:
                    location_el = item.select_one("[class*='location']")

                if not link_el:
                    continue

                href = link_el.get("href", "")
                url = "https://www.coches.net" + href if href.startswith("/") else href
                external_id = href.strip("/").split("/")[-1]
                title = title_el.text.strip() if title_el else ""
                price_text = price_el.text.strip().replace(".", "").replace("€", "").replace(",", "").strip() if price_el else None
                price = int(price_text) if price_text and price_text.isdigit() else None
                image_url = image_el.get("src") or image_el.get("data-src") if image_el else None
                location = location_el.text.strip() if location_el else ""

                if not external_id or not title:
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
            except Exception as e:
                print(f"Coches item error: {e}")
                continue

        print(f"Coches results: {len(results)}")
        return results
