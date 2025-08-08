"""
AutoSlides MCP – Runtime principal
=================================

Exponer un endpoint JSON-RPC /mcp conforme al manifiesto y un endpoint
conveniencia /generate que orquesta todo el flujo y devuelve el .pptx.

Uso rápido:
-----------
    uvicorn main:app --reload

Variables de entorno relevantes:
    OPENAI_API_KEY           – clave del LLM
    UNSPLASH_ACCESS_KEY      – clave API de Unsplash
    SLIDE_TEMPLATE           – ruta opcional .potx
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Mapping

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tools import scripts, images, slides

# ---------------------------------------------------------------------------
# Registro dinámico de herramientas a partir del manifest.yaml
# ---------------------------------------------------------------------------

# Map tool name → callable
TOOLS: Mapping[str, Callable[..., Any]] = {
    "write_script": scripts.write_script,
    "fetch_images": images.fetch_images,
    "create_slide": slides.create_slide,
    "export_pptx": slides.export_pptx,
}


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------

app = FastAPI(title="AutoSlides MCP", version="0.1.0")

# Habilita CORS sencillo para pruebas con frontends locales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Esquemas Pydantic
# ---------------------------------------------------------------------------

class MCPRequest(BaseModel):
    tool: str = Field(example="write_script")
    args: Dict[str, Any] = Field(default_factory=dict)


class GenerateRequest(BaseModel):
    topic: str = Field(example="Energía eólica")
    slides: int = Field(default=6, ge=1, le=20)
    tone: str = Field(default="neutral", example="inspirador")
    images_per_slide: int = Field(default=1, ge=0, le=4)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/.well-known/mcp/manifest.yaml")
def manifest():
    return FileResponse("manifest.yaml", media_type="text/yaml")

@app.post("/mcp")
async def mcp_router(payload: MCPRequest):
    """Endpoint genérico MCP → ejecuta la herramienta solicitada."""
    if payload.tool not in TOOLS:
        raise HTTPException(400, f"Tool desconocida: {payload.tool}")

    try:
        result = TOOLS[payload.tool](**payload.args)
    except TypeError as exc:
        raise HTTPException(400, f"Argumentos inválidos: {exc}")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Error al ejecutar {payload.tool}: {exc}")

    return {"tool": payload.tool, "return": result}


@app.post("/generate")
async def generate_deck(req: GenerateRequest):
    """Pipeline alto nivel: genera toda la presentación y entrega la ruta."""
    # 1. Guion con el LLM
    script_data = scripts.write_script(req.topic, req.slides, req.tone)

    # 2. Para cada slide genera imágenes y compone la diapositiva
    for slide_data in script_data["slides"]:
        img_urls: list[str] = []
        if req.images_per_slide:
            img_urls = images.fetch_images(slide_data["title"], req.images_per_slide)

        slides.create_slide(
            title=slide_data["title"],
            bullets=slide_data["bullets"],
            images=img_urls,
        )

    # 3. Exporta y devuelve la ruta absoluta
    filename = f"{req.topic.replace(' ', '')}.pptx"
    file_path = slides.export_pptx(filename)

    return {"file": file_path}


# Punto de entrada conveniente: `python main.py`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)