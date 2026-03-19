# oncall_app.py  (FastAPI 版・React フロントエンド)
# -------------------------------------------------------------------
#  起動例:
#     pip install fastapi uvicorn pandas jpholiday python-multipart
#     cd frontend && npm install && npm run build
#     uvicorn oncall_app.oncall_app:app --reload
# -------------------------------------------------------------------

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routes import app

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def serve_spa():
    return FileResponse(STATIC_DIR / "index.html")


# SPA の client-side routing に対応: /calendar, /schedule は index.html を返す
@app.get("/calendar")
@app.get("/schedule")
async def serve_spa_routes():
    return FileResponse(STATIC_DIR / "index.html")


# ビルド済みアセット配信
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
