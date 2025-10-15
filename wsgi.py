import importlib

# ננסה לאתר את האפליקציה הקיימת (FastAPI/Starlette/Flask) כדי לא לשבור כלום
existing_app = None
for name in ("app.main", "app", "main"):
    try:
        m = importlib.import_module(name)
        maybe = getattr(m, "app", None)
        if maybe is not None:
            existing_app = maybe
            break
    except Exception:
        pass

# אם זו אפליקציית Flask, נעטוף ל-ASGI
try:
    from flask import Flask  # type: ignore
    from starlette.middleware.wsgi import WSGIMiddleware  # type: ignore
    if existing_app is not None and isinstance(existing_app, Flask):
        existing_app = WSGIMiddleware(existing_app)
except Exception:
    pass

# ה-API החדש של /api/contact
from app.api_contact import app as contact_api

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import PlainTextResponse

routes = [
    Mount("/static", app=StaticFiles(directory="app/static"), name="static"),
    Mount("/api", app=contact_api),   # כאן ה-API של טופס 'צור קשר'
]

if existing_app is not None:
    routes.append(Mount("/", app=existing_app))
else:
    async def root(scope, receive, send):
        resp = PlainTextResponse("OK (no existing app found)")
        await resp(scope, receive, send)
    routes.append(Mount("/", app=root))

app = Starlette(routes=routes)

# בסוף הקובץ app/api_contact.py (או קרוב להגדרות ה-FastAPI)
@app.get("/healthz")
def healthz():
    return {"ok": True}
