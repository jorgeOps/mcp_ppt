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
from typing import Any, Callable, Dict, Mapping, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from tools import scripts, images, slides
from utils import slugify

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

SLIDES_DIR = Path("slides")
SLIDES_DIR.mkdir(exist_ok=True)

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
    filename: Optional[str] = None
    notes: Optional[str] = None

class RPCReq(BaseModel):
    jsonrpc: str
    id: int | str
    method: str
    params: Dict[str, Any] = {}

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.api_route("/.well-known/mcp/manifest.yaml", methods=["GET", "HEAD"])
def manifest():
    return FileResponse("manifest.yaml", media_type="text/yaml")


@app.get("/download/{filename}")
def download(filename: str):
    fp = (SLIDES_DIR / filename).resolve()
    if not str(fp).startswith(str(SLIDES_DIR.resolve())):
        raise HTTPException(400, "Ruta inválida")
    if not fp.exists():
        raise HTTPException(404, "Archivo no encontrado")

    return FileResponse(
        fp,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=fp.name,
    )


@app.post("/mcp")
def mcp_rpc(req: RPCReq):
    if req.jsonrpc != "2.0":
        raise HTTPException(400, "jsonrpc must be '2.0'")
    if req.method not in TOOLS:
        raise HTTPException(400, f"Unknown method {req.method}")
    try:
        result = TOOLS[req.method](**req.params)
    except TypeError as e:
        raise HTTPException(400, f"Bad params: {e}")
    except Exception as e:
        # error estándar JSON-RPC
        return {"jsonrpc":"2.0","id":req.id,"error":{"code":-32000,"message":str(e)}}
    return {"jsonrpc":"2.0","id":req.id,"result":result}


@app.post("/generate")
async def generate_deck(req: GenerateRequest, request: Request):
    """Pipeline alto nivel: genera toda la presentación y entrega la ruta."""
    # 1. Guion con el LLM
    script_data = scripts.write_script(req.topic, req.slides, req.tone)
    if isinstance(script_data, str):
        import json
        script_data = json.loads(script_data)

    if not isinstance(script_data, dict) or "slides" not in script_data:
        raise HTTPException(500, "El LLM no devolvió un JSON válido con 'slides'.")

    # 2. Para cada slide genera imágenes y compone la diapositiva
    for slide_data in script_data["slides"]:
        img_urls: list[str] = []
        if req.images_per_slide:
            img_urls = images.fetch_images(slide_data["title"], req.images_per_slide)

        slides.create_slide(
            title=slide_data["title"],
            bullets=slide_data["bullets"],
            images=img_urls,
            notes=req.notes,
        )

    # 3. Exporta y devuelve la ruta absoluta
    base = req.filename or slugify(req.topic)
    fname = f"{base}.pptx"
    file_path = slides.export_pptx(str(SLIDES_DIR / fname))

    download_url = str(request.url_for("download", filename=Path(file_path).name))
    return {
        "file": file_path,
        "url": download_url,
        "slides": len(script_data["slides"]),
        "topic": script_data.get("topic", req.topic),
    }


# Punto de entrada conveniente: `python main.py`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)