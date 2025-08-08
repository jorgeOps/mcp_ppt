"""
AutoSlides MCP – Herramientas de imágenes
========================================
Descarga URLs de imágenes libres de Unsplash con manejo de errores,
parámetros opcionales y validación de la API key.
"""

from __future__ import annotations

import os
import random
from typing import List
from dotenv import load_dotenv

import httpx

# ---------------------------------------------------------------------------
# Configuración del cliente Unsplash
# ---------------------------------------------------------------------------
#   1. Crea tu app en https://unsplash.com/developers y copia el Access Key.
#   2. Exporta en tu entorno:  export UNSPLASH_ACCESS_KEY="abc123…"
# ---------------------------------------------------------------------------

load_dotenv()
UNSPLASH_ACCESS_KEY: str | None = os.getenv("UNSPLASH_ACCESS_KEY")
if not UNSPLASH_ACCESS_KEY:
    raise RuntimeError(
        "UNSPLASH_ACCESS_KEY no está definido. Ve a https://unsplash.com/developers, "
        "crea una aplicación gratuita y exporta la clave, por ejemplo:\n"
        "  export UNSPLASH_ACCESS_KEY='<tu_access_key>'"
    )

# Cliente HTTPX persistente (reutiliza conexiones)
_client = httpx.Client(
    base_url="https://api.unsplash.com",
    timeout=10.0,
    headers={
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
        "User-Agent": "autoslides-mcp/0.1",
    },
)


# ---------------------------------------------------------------------------
# Tool MCP: fetch_images
# ---------------------------------------------------------------------------

def fetch_images(
    query: str,
    n: int = 1,
    *,
    orientation: str | None = None,  # "landscape", "portrait", "squarish"
    max_per_call: int = 30,
) -> List[str]:
    """Devuelve hasta *n* URLs de imágenes coherentes con la búsqueda.

    Unsplash limita `per_page` a 30. Si `n` > 30 hacemos varias paginaciones.
    Si la búsqueda no arroja resultados, devolvemos una URL de placeholder.
    """

    if n < 1 or n > 50:
        raise ValueError("n debe estar entre 1 y 50 para evitar rate‑limits excesivos")

    # Parámetros base de la búsqueda
    per_page = min(max_per_call, n)
    collected: list[str] = []
    page = 1

    while len(collected) < n:
        params = {
            "query": query,
            "page": page,
            "per_page": per_page,
        }
        if orientation:  # opcional
            params["orientation"] = orientation

        r = _client.get("/search/photos", params=params)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Unsplash API error {exc.response.status_code}: {exc.response.text}"
            ) from exc

        payload = r.json()
        photos = payload.get("results", [])
        if not photos:
            break  # sin más resultados

        collected.extend(p["urls"]["regular"] for p in photos)

        # Siguiente página
        page += 1
        if page > payload.get("total_pages", 0):
            break

    # Si no se obtuvo ninguna imagen, fallback genérico
    if not collected:
        fallback = "https://dummyimage.com/800x600/cccccc/000000&text=Sin+imagen"
        return [fallback] * n

    random.shuffle(collected)  # algo de variabilidad
    return collected[:n]
