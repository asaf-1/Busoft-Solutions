# wsgi.py — גרסה יציבה בלי Jinja2

import importlib
import os
from typing import Optional, Any

# נסה לאתר אפליקציה קיימת (FastAPI/Starlette/Flask)
existing_app: Optional[Any] = None
for name in ("app.main", "app", "main"):
    try:
        m = importlib.import_module(name)
        maybe = getattr(m, "app", None)
        if maybe is not None:
            existing_app = maybe
            break
    except Exception:
        pass

# עטיפת Flask ל-ASGI אם צריך
try:
    from flask import Flask  # type: ignore
    from starlette.middleware.wsgi import WSGIMiddleware  # type: ignore
    if existing_app is not None and isinstance(existing_app, Flask):
        existing_app = WSGIMiddleware(existing_app)
except Exception:
    pass

# --- אפליקציית האיחוד (FastAPI) ---
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Busoft")

# סטטי – גם /static וגם /assets
if os.path.isdir("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
if os.path.isdir("app/static/assets"):
    app.mount("/assets", StaticFiles(directory="app/static/assets"), name="assets")

# בריאות ל-Render
@app.get("/healthz")
async def healthz():
    return {"ok": True}

# API של צור קשר
try:
    from app.api_contact import app as contact_api
    app.mount("/api", contact_api)  # /api/contact
except Exception as e:
    @app.get("/api/contact")
    async def _api_error():
        return {"ok": False, "error": f"contact api not loaded: {e}"}

# אתר קיים? נמפה לשורש. אחרת – נחזיר index.html כקובץ
if existing_app is not None:
    app.mount("/", existing_app)
else:
    INDEX = os.path.join("app", "templates", "index.html")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        if os.path.isfile(INDEX):
            # שולח את ה-HTML כקובץ (אין צורך ב-Jinja2)
            return FileResponse(INDEX, media_type="text/html; charset=utf-8")
        return HTMLResponse("<h1>Busoft</h1><p>OK</p>")
