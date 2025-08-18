AutoSlides MCP – Generador automático de presentaciones PowerPoint
==================================================================

Descripción
-----------
AutoSlides MCP es una herramienta que crea presentaciones PowerPoint (.pptx) a partir de temas en lenguaje natural. Utiliza modelos de lenguaje (OpenAI) para generar el guion y la estructura de las diapositivas, y descarga imágenes libres de Unsplash para enriquecer visualmente cada slide. Todo el proceso es automático y configurable mediante endpoints HTTP.

Estructura del proyecto
-----------------------
´´´text
- main.py                → Runtime principal con API FastAPI.
- manifest.yaml          → Especificación de herramientas y parámetros (JSON-RPC).
- requirements.txt       → Dependencias Python.
- runtime.txt            → Versión de Python recomendada.
- tools/
    ├─ scripts.py        → Genera el guion de la presentación usando OpenAI.
    ├─ images.py         → Descarga imágenes libres de Unsplash.
    ├─ slides.py         → Composición y exportación de diapositivas (.pptx).
    └─ __init__.py
- utils/
    └─ slugify.py        → Convierte títulos en nombres de archivo seguros.
  ```

Cómo funciona
-------------
1. El usuario solicita una presentación indicando el tema, número de diapositivas, tono y cantidad de imágenes por slide.
2. El sistema genera el guion (títulos y viñetas) usando OpenAI.
3. Para cada diapositiva, busca imágenes relevantes en Unsplash.
4. Compone cada slide con título, viñetas e imágenes, y añade notas si se desea.
5. Exporta el archivo .pptx y lo deja disponible para descarga.

Endpoints principales
---------------------
- POST /generate
    Orquesta todo el flujo: recibe parámetros y devuelve la ruta y URL de descarga del .pptx generado.
- POST /mcp
    Endpoint JSON-RPC conforme al manifest.yaml para invocar herramientas individuales (write_script, fetch_images, create_slide, export_pptx).
- GET /.well-known/mcp/manifest.yaml
    Devuelve el manifiesto de herramientas y parámetros.
- GET /download/{filename}
    Descarga el archivo .pptx generado.

Variables de entorno necesarias
-------------------------------
- OPENAI_API_KEY           → Clave de API de OpenAI (para generación de guion).
- UNSPLASH_ACCESS_KEY      → Clave de API de Unsplash (para imágenes libres).
- SLIDE_TEMPLATE           → Ruta opcional a una plantilla .potx para personalizar el diseño.

Instalación y ejecución
-----------------------
1. Instala las dependencias:
   pip install -r requirements.txt

2. Exporta tus claves de API:
   export OPENAI_API_KEY="sk-..."
   export UNSPLASH_ACCESS_KEY="abc123..."

3. (Opcional) Define una plantilla personalizada:
   export SLIDE_TEMPLATE="/ruta/a/mi_template.potx"

4. Ejecuta el servidor:
   uvicorn main:app --reload

5. Accede a los endpoints desde tu frontend, Postman, o curl.

Notas adicionales
-----------------
- El layout de las diapositivas está optimizado para claridad: viñetas a la izquierda (~55%), imágenes a la derecha (~45%), y título siempre visible. Esto es fijo. En futuras versiones se podría mejorar el layout.
- Los nombres de archivo se generan automáticamente a partir del tema usando [`slugify`](utils/slugify.py).
- Puedes personalizar el número de imágenes por slide y el tono del texto generado.
