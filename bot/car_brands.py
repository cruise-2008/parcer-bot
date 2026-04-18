import difflib

BRANDS = [
    "Abarth", "Alfa Romeo", "Aston Martin", "Audi", "Bentley", "BMW", "Bugatti",
    "Cadillac", "Chevrolet", "Chrysler", "Citroen", "Cupra", "Dacia", "Daewoo",
    "Dodge", "Ferrari", "Fiat", "Ford", "Genesis", "Honda", "Hyundai", "Infiniti",
    "Jaguar", "Jeep", "Kia", "Lamborghini", "Lancia", "Land Rover", "Lexus",
    "Maserati", "Mazda", "Mercedes-Benz", "Mini", "Mitsubishi", "Nissan", "Opel",
    "Peugeot", "Porsche", "Renault", "Rolls-Royce", "Seat", "Skoda", "Smart",
    "Subaru", "Suzuki", "Tesla", "Toyota", "Volkswagen", "Volvo", "BYD"
]

BRANDS_LOWER = {b.lower(): b for b in BRANDS}

TYPO_MAP = {
    "тоета": "Toyota", "тойота": "Toyota", "toyotta": "Toyota", "toyata": "Toyota",
    "бмв": "BMW", "bmw": "BMW",
    "мерседес": "Mercedes-Benz", "mercedes": "Mercedes-Benz",
    "ауди": "Audi", "фольксваген": "Volkswagen", "vw": "Volkswagen",
    "хонда": "Honda", "ниссан": "Nissan", "хундай": "Hyundai",
    "киа": "Kia", "рено": "Renault", "пежо": "Peugeot",
    "ситроен": "Citroen", "опель": "Opel", "форд": "Ford",
    "фиат": "Fiat", "сеат": "Seat", "шкода": "Skoda",
    "лексус": "Lexus", "мазда": "Mazda", "субару": "Subaru",
    "сузуки": "Suzuki", "митсубиси": "Mitsubishi", "вольво": "Volvo",
    "порше": "Porsche", "ягуар": "Jaguar", "тесла": "Tesla",
}

def find_brand(text: str) -> tuple[str | None, float]:
    text_lower = text.strip().lower()

    if text_lower in TYPO_MAP:
        return TYPO_MAP[text_lower], 1.0

    if text_lower in BRANDS_LOWER:
        return BRANDS_LOWER[text_lower], 1.0

    matches = difflib.get_close_matches(text_lower, BRANDS_LOWER.keys(), n=1, cutoff=0.6)
    if matches:
        return BRANDS_LOWER[matches[0]], difflib.SequenceMatcher(None, text_lower, matches[0]).ratio()

    return None, 0.0
