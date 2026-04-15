from abc import ABC, abstractmethod
from typing import List
from db.models import Listing, Search

class BaseScraper(ABC):

    @abstractmethod
    async def fetch(self, search: Search) -> List[Listing]:
        pass

    def build_listing(self, external_id, platform, title, price, url, image_url, location) -> Listing:
        return Listing(
            external_id=str(external_id),
            platform=platform,
            title=title,
            price=price,
            url=url,
            image_url=image_url,
            location=location
        )
