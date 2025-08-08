"""
AutoSlides MCP – Herramientas de guion
====================================
Esta herramienta genera el guion (título + viñetas) de una presentación
utilizando un modelo de lenguaje.  Envuelve la llamada a OpenAI con
manejador de errores y validación JSON.
"""

import os
from dotenv import load_dotenv
import json
from typing import List, Dict, Any
from openai import OpenAI, APIError

# ---------------------------------------------------------------------------
# Configuración del cliente
# ---------------------------------------------------------------------------
#   1. Exporta tu clave antes de lanzar el runtime:
#        export OPENAI_API_KEY="sk-..."
#   2. (Opcional) Cambia el modelo por otro disponible en tu cuenta.
# ---------------------------------------------------------------------------

load_dotenv()
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY no está definido. Obtén tu clave en "
        "https://platform.openai.com/ y expórtala, por ejemplo:\n"
        "  export OPENAI_API_KEY='<tu_clave>'"
    )

# Inicializa el cliente una sola vez, reutilizable por todo el runtime
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------------
# Llamada centralizada al LLM
# ---------------------------------------------------------------------------

def _call_llm(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Envuelve la llamada a chat.completions y maneja errores/reintentos"""
    try:
        rsp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
            timeout=60,
        )
    except APIError as exc:
        # Propaga como RuntimeError para que FastAPI lo serialice en 500.
        raise RuntimeError(f"Error en la API de OpenAI: {exc}") from exc

    return rsp.choices[0].message.content  # cadena JSON cruda

# ---------------------------------------------------------------------------
# Tool MCP: write_script
# ---------------------------------------------------------------------------

def write_script(topic: str, slides: int, tone: str = "neutral") -> Dict[str, Any]:
    """Genera el guion de una presentación.

    Parameters
    ----------
    topic : str
        Tema central de la presentación.
    slides : int
        Número de diapositivas a generar (1‑20 recomendado).
    tone : str, optional
        Tono general del texto (neutral, informal, inspirador…), by default "neutral".

    Returns
    -------
    dict
        {
          "topic": "...",
          "slides": [
             {"title": "…", "bullets": ["…", "…"]},
             ...
          ]
        }
    """

    # Prompt con especificación estricta de formato JSON
    prompt = (
        f"Redacta un guion de {slides} diapositivas sobre '{topic}' "
        f"en tono {tone}. Devuelve SOLO un JSON con la forma:\n"
        "{\n  \"slides\": [\n    {\"title\": str, \"bullets\": [str, ...]},\n    ...\n  ]\n}\n"
        "Sin texto fuera del JSON. Sin comentarios."
    )

    raw_json: str = _call_llm(prompt)

    # Parseo y validación rápida
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "El modelo devolvió JSON inválido. Contenido devuelto:\n" + raw_json
        ) from exc

    if "slides" not in data or not isinstance(data["slides"], list):
        raise ValueError(
            "Estructura inesperada: falta la clave 'slides'. Contenido:\n" + raw_json
        )

    # Ajusta longitud si el modelo no respeta exactamente el nº pedido
    if len(data["slides"]) != slides:
        data["slides"] = data["slides"][:slides]

    return {"topic": topic, **data}
