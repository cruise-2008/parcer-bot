from dataclasses import dataclass
from typing import Optional

@dataclass
class Search:
    id: int
    user_id: int
    keyword: str
    price_min: int
    price_max: int
    location: str
    radius: int
    active: bool

@dataclass
class Listing:
    external_id: str
    platform: str
    title: str
    price: Optional[int]
    url: str
    image_url: Optional[str]
    location: Optional[str]
