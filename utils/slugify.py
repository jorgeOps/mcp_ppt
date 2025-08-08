import unicodedata

def slugify(text: str) -> str:
    """
    Convierte 'Energía solar — 2025' -> 'energia-solar-2025'
    """
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    safe = []
    for ch in text.lower():
        if ch.isalnum():
            safe.append(ch)
        elif ch in (" ", "-", "_", "."):
            safe.append("-")
    slug = "".join(safe)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "deck"