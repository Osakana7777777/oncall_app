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


# ビルド済みアセット配信
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


# SPA ルーティング: /api と /csv と /assets を除くすべて index.html を返す
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(STATIC_DIR / "index.html")
