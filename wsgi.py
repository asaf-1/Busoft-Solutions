# wsgi.py  — גרסה יציבה מלאה
import importlib
from typing import Optional, Any
import os

# --- 1) נסה לאתר אפליקציה קיימת (FastAPI/Starlette/Flask) ---
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

# --- 2) API של צור קשר ---
try:
    from app.api_contact import app as contact_api  # FastAPI
except Exception as e:  # לא לחסום עלייה אם משהו חסר
    from fastapi import FastAPI
    contact_api = FastAPI(title="contact-api-stub")
    @contact_api.get("/contact")
    async def _stub():
        return {"ok": False, "error": "api_contact not loaded", "detail": str(e)}

# --- 3) אפליקציה מאחדת (FastAPI) עם /healthz + מיפויים ---
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

app = FastAPI(title="Busoft")

# סטטי — גם /static וגם /assets (כדי לכסות כל נתיב ב-HTML)
if os.path.isdir("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
if os.path.isdir("app/static/assets"):
    app.mount("/assets", StaticFiles(directory="app/static/assets"), name="assets")

# בריאות
@app.get("/healthz")
async def healthz():
    return {"ok": True}

# ה-API
app.mount("/api", contact_api)           # /api/contact

# אתר קיים או fallback ל-index.html אם קיים
if existing_app is not None:
    app.mount("/", existing_app)         # האתר שלך כמו שהוא
else:
    templates_dir = "app/templates"
    templates = Jinja2Templates(directory=templates_dir) if os.path.isdir(templates_dir) else None

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        if templates and os.path.isfile(os.path.join(templates_dir, "index.html")):
            return templates.TemplateResponse("index.html", {"request": request})
        return HTMLResponse("<h1>Busoft</h1><p>OK</p>")
