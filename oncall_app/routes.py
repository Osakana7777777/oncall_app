import io
import json
import os
import secrets
import time
import uuid
import calendar
import datetime as _dt
from collections import OrderedDict
from typing import Dict, List, Optional, Set

import pandas as pd
from fastapi import Depends, FastAPI, Form, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from .holiday_utils import is_holiday
from .scheduler import make_schedule, DEFAULT_COUNT
from . import db

app = FastAPI(title="当直スケジューラ")

db.init_db()

MAX_DOCTORS = 100
MAX_COUNT = 62  # 1か月の最大スロット数 (31日 × 2枠)

_CSV_TTL_SECONDS = 60 * 60
_CSV_CACHE_MAX = 200
_csv_cache: "OrderedDict[str, tuple]" = OrderedDict()


def _csv_cache_put(tok: str, txt: str) -> None:
    now = time.time()
    expired = [k for k, (ts, _) in _csv_cache.items() if now - ts > _CSV_TTL_SECONDS]
    for k in expired:
        del _csv_cache[k]
    while len(_csv_cache) >= _CSV_CACHE_MAX:
        _csv_cache.popitem(last=False)
    _csv_cache[tok] = (now, txt)


def _csv_cache_get(tok: str) -> Optional[str]:
    item = _csv_cache.get(tok)
    if item is None:
        return None
    ts, txt = item
    if time.time() - ts > _CSV_TTL_SECONDS:
        del _csv_cache[tok]
        return None
    return txt


def require_admin(x_admin_token: str = Header(default="")):
    """ADMIN_TOKEN 環境変数が設定されている場合のみ認証を要求する。"""
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected:
        return
    if not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="管理トークンが必要です。")


def _build_weeks(y: int, m: int) -> list:
    weeks = []
    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(y, m):
        week_data = []
        for day in week:
            week_data.append({
                "date": str(day),
                "day": day.day,
                "month": day.month,
                "weekday": day.weekday(),
                "is_holiday": bool(is_holiday(day)),
                "in_month": day.month == m,
            })
        weeks.append(week_data)
    return weeks


def _parse_counts(raw: str, doc_list: List[str]) -> Dict[str, int]:
    """counts (JSON 文字列) を医師名→回数 dict に変換。未指定の医師はデフォルト値。"""
    parsed: Dict[str, int] = {}
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=422, detail=f"counts の形式が不正です: {e}")
        if not isinstance(data, dict):
            raise HTTPException(status_code=422, detail="counts はオブジェクトで指定してください。")
        for k, v in data.items():
            try:
                n = int(v)
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail=f"{k} の当直回数が数値ではありません。")
            if n < 0:
                raise HTTPException(status_code=422, detail=f"{k} の当直回数は 0 以上にしてください。")
            if n > MAX_COUNT:
                raise HTTPException(status_code=422, detail=f"{k} の当直回数は {MAX_COUNT} 以下にしてください。")
            parsed[k] = n
    return {d: parsed.get(d, DEFAULT_COUNT) for d in doc_list}


def _parse_docs(docs: str) -> List[str]:
    doc_list = [d.strip() for d in docs.split(",") if d.strip()]
    if len(doc_list) > MAX_DOCTORS:
        raise HTTPException(status_code=422, detail=f"医師は最大 {MAX_DOCTORS} 名までです。")
    return doc_list


def _validate_year_month(year: int, month: int) -> None:
    if not 1 <= month <= 12:
        raise HTTPException(status_code=422, detail="月は 1〜12 で指定してください。")
    if not 1900 <= year <= 2100:
        raise HTTPException(status_code=422, detail="年は 1900〜2100 で指定してください。")


def _validate_gaps(gap_lo: int, gap_hi: int) -> None:
    if not 1 <= gap_lo <= gap_hi <= 31:
        raise HTTPException(
            status_code=422,
            detail="シフト間隔は 1〜31 の範囲で、最小 ≤ 最大 となるように指定してください。",
        )


@app.post("/api/calendar")
async def api_calendar(
    year: int = Form(...),
    month: int = Form(...),
    docs: str = Form(...),
    gap_lo: int = Form(...),
    gap_hi: int = Form(...),
    counts: str = Form(""),
):
    _validate_year_month(year, month)
    _validate_gaps(gap_lo, gap_hi)
    doc_list = _parse_docs(docs)
    counts_map = _parse_counts(counts, doc_list)
    weeks = _build_weeks(year, month)
    return JSONResponse({
        "year": year,
        "month": month,
        "docs": doc_list,
        "weeks": weeks,
        "gap_lo": gap_lo,
        "gap_hi": gap_hi,
        "counts": counts_map,
    })


@app.post("/api/schedule")
async def api_schedule(
    year: int = Form(...),
    month: int = Form(...),
    docs: str = Form(...),
    unavail: str = Form(""),
    gap_lo: int = Form(...),
    gap_hi: int = Form(...),
    counts: str = Form(""),
):
    _validate_year_month(year, month)
    _validate_gaps(gap_lo, gap_hi)
    doc_list = _parse_docs(docs)
    counts_map = _parse_counts(counts, doc_list)
    unavailable: Dict[str, Set[tuple]] = {d: set() for d in doc_list}
    if unavail:
        for item in unavail.split(","):
            if not item:
                continue
            try:
                doc, date_str, tag = item.split("|")
                dt = _dt.date.fromisoformat(date_str)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"unavail の形式が不正です: {item}")
            if doc not in unavailable:
                raise HTTPException(status_code=422, detail=f"医師名が一致しません: {doc}")
            if tag == "DAY":
                if dt.weekday() >= 5 or is_holiday(dt):
                    unavailable[doc].add((dt, "WE_DAY"))
            else:
                if dt.weekday() >= 5 or is_holiday(dt):
                    unavailable[doc].add((dt, "WE_NIGHT"))
                else:
                    unavailable[doc].add((dt, "WD_NIGHT"))
    try:
        rows = make_schedule(
            year, month, doc_list, unavailable,
            gap_lo=gap_lo, gap_hi=gap_hi, counts=counts_map,
        )
    except (RuntimeError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=422)

    df = pd.DataFrame(rows)
    tok = uuid.uuid4().hex
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    _csv_cache_put(tok, buf.getvalue())
    serializable_rows = [
        {"Date": str(r["Date"]), "Shift": r["Shift"], "Doctor": r["Doctor"]}
        for r in rows
    ]
    return JSONResponse({
        "year": year,
        "month": month,
        "rows": serializable_rows,
        "tok": tok,
    })


@app.get("/csv", response_class=StreamingResponse)
async def download_csv(tok: str):
    txt = _csv_cache_get(tok)
    if txt is None:
        return JSONResponse({"error": "リンクが無効です。"}, status_code=404)
    return StreamingResponse(
        io.BytesIO(txt.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shift.csv"},
    )


# -------------------------------------------------------------------
# アンケート (医師が入れない日を事前に申告)
# -------------------------------------------------------------------


def _survey_public(survey: dict) -> dict:
    return {
        "id": survey["id"],
        "title": survey["title"],
        "year": survey["year"],
        "month": survey["month"],
        "docs": survey["docs"],
        "counts": survey.get("counts", {d: DEFAULT_COUNT for d in survey["docs"]}),
        "gap_lo": survey["gap_lo"],
        "gap_hi": survey["gap_hi"],
        "created_at": survey["created_at"],
        "weeks": _build_weeks(survey["year"], survey["month"]),
    }


@app.post("/api/surveys", dependencies=[Depends(require_admin)])
async def create_survey(
    title: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    docs: str = Form(...),
    gap_lo: int = Form(5),
    gap_hi: int = Form(8),
    counts: str = Form(""),
):
    _validate_year_month(year, month)
    _validate_gaps(gap_lo, gap_hi)
    doc_list = _parse_docs(docs)
    if not doc_list:
        raise HTTPException(status_code=422, detail="医師名を1名以上入力してください。")
    counts_map = _parse_counts(counts, doc_list)
    survey_id = uuid.uuid4().hex[:12]
    db.create_survey(
        survey_id, title.strip() or f"{year}年{month}月", year, month,
        doc_list, gap_lo, gap_hi, counts_map,
    )
    return JSONResponse({"id": survey_id})


@app.get("/api/surveys", dependencies=[Depends(require_admin)])
async def list_surveys():
    return JSONResponse({"surveys": db.list_surveys()})


@app.get("/api/surveys/{survey_id}")
async def get_survey(survey_id: str):
    survey = db.get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="アンケートが見つかりません。")
    return JSONResponse(_survey_public(survey))


@app.delete("/api/surveys/{survey_id}", dependencies=[Depends(require_admin)])
async def delete_survey(survey_id: str):
    if not db.delete_survey(survey_id):
        raise HTTPException(status_code=404, detail="アンケートが見つかりません。")
    return JSONResponse({"ok": True})


@app.get("/api/surveys/{survey_id}/responses/{doctor}")
async def get_survey_response(survey_id: str, doctor: str):
    survey = db.get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="アンケートが見つかりません。")
    if doctor not in survey["docs"]:
        raise HTTPException(status_code=404, detail="この医師はアンケート対象ではありません。")
    resp = db.get_response(survey_id, doctor)
    return JSONResponse({"response": resp})


@app.post("/api/surveys/{survey_id}/responses")
async def submit_survey_response(
    survey_id: str,
    doctor: str = Form(...),
    blocked: str = Form(""),
):
    survey = db.get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="アンケートが見つかりません。")
    if doctor not in survey["docs"]:
        raise HTTPException(status_code=422, detail="医師名が一致しません。")

    items: List[str] = []
    if blocked:
        for item in blocked.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                date_str, tag = item.split("|")
                _dt.date.fromisoformat(date_str)
            except ValueError:
                raise HTTPException(status_code=422, detail=f"不正な値: {item}")
            if tag not in ("DAY", "NIGHT"):
                raise HTTPException(status_code=422, detail=f"不正なタグ: {tag}")
            items.append(f"{date_str}|{tag}")

    db.upsert_response(survey_id, doctor, items)
    return JSONResponse({"ok": True, "count": len(items)})


@app.get("/api/surveys/{survey_id}/results", dependencies=[Depends(require_admin)])
async def get_survey_results(survey_id: str):
    survey = db.get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="アンケートが見つかりません。")
    responses = db.list_responses(survey_id)
    responded = {r["doctor"] for r in responses}
    pending = [d for d in survey["docs"] if d not in responded]
    return JSONResponse({
        "survey": _survey_public(survey),
        "responses": responses,
        "pending": pending,
    })
