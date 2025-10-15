import importlib
from typing import Optional

# ננסה למצוא app=... ב-app.py / app/main.py / main.py
app: Optional[object] = None
for mod_name in ("app", "app.main", "main"):
    try:
        mod = importlib.import_module(mod_name)
        candidate = getattr(mod, "app", None)
        if candidate is not None:
            app = candidate
            break
    except Exception:
        continue

# אם זה Flask - לעטוף ל-ASGI
try:
    from flask import Flask  # type: ignore
    from uvicorn.middleware.wsgi import WSGIMiddleware  # type: ignore
    if app is not None and isinstance(app, Flask):
        app = WSGIMiddleware(app)
except Exception:
    pass

# אם לא נמצא כלום - fallback סטטי בסיסי
if app is None:
    from flask import Flask, send_from_directory  # type: ignore
    from uvicorn.middleware.wsgi import WSGIMiddleware  # type: ignore
    flask_app = Flask(__name__, static_folder="app/static", static_url_path="/static")
    @flask_app.route("/")
    def root():
        # אם יש index.html בתבניות – הגש אותו; אחרת הגש סטטי
        try:
            return send_from_directory("app/templates", "index.html")
        except Exception:
            return send_from_directory("app/static", "index.html")
    app = WSGIMiddleware(flask_app)

# *** להבטיח ש-/static תמיד יעבוד ***
from starlette.applications import Starlette  # type: ignore
from starlette.routing import Mount  # type: ignore
from starlette.staticfiles import StaticFiles  # type: ignore

star = Starlette(routes=[
    # קבצי סטטיק מתוך app/static על /static
    Mount("/static", app=StaticFiles(directory="app/static"), name="static"),
    # כל השאר – לאפליקציה שלך (FastAPI/WSGI עטוף)
    Mount("/", app=app),
])

app = star
