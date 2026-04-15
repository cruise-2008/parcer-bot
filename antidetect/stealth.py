import asyncio
import random
from fake_useragent import UserAgent

ua = UserAgent()

def get_headers():
    return {
        "User-Agent": ua.random,
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

async def random_delay():
    await asyncio.sleep(random.uniform(1.5, 4.0))
