import io
import uuid
import calendar
import datetime as _dt
from typing import Dict, List, Set

import pandas as pd
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from .holiday_utils import is_holiday
from .scheduler import make_schedule
from . import db

app = FastAPI(title="当直スケジューラ")

db.init_db()

_csv_cache: Dict[str, str] = {}


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


@app.post("/api/calendar")
async def api_calendar(
    year: int = Form(...),
    month: int = Form(...),
    docs: str = Form(...),
    gap_lo: int = Form(...),
    gap_hi: int = Form(...),
):
    doc_list = [d.strip() for d in docs.split(",") if d.strip()]
    weeks = _build_weeks(year, month)
    return JSONResponse({
        "year": year,
        "month": month,
        "docs": doc_list,
        "weeks": weeks,
        "gap_lo": gap_lo,
        "gap_hi": gap_hi,
    })


@app.post("/api/schedule")
async def api_schedule(
    year: int = Form(...),
    month: int = Form(...),
    docs: str = Form(...),
    unavail: str = Form(""),
    gap_lo: int = Form(...),
    gap_hi: int = Form(...),
):
    doc_list = [d.strip() for d in docs.split(",") if d.strip()]
    unavailable: Dict[str, Set[tuple]] = {d: set() for d in doc_list}
    if unavail:
        for item in unavail.split(","):
            if not item:
                continue
            doc, date_str, tag = item.split("|")
            dt = _dt.date.fromisoformat(date_str)
            if tag == "DAY":
                if dt.weekday() >= 5 or is_holiday(dt):
                    unavailable[doc].add((dt, "WE_DAY"))
            else:
                if dt.weekday() >= 5 or is_holiday(dt):
                    unavailable[doc].add((dt, "WE_NIGHT"))
                else:
                    unavailable[doc].add((dt, "WD_NIGHT"))
    try:
        rows = make_schedule(year, month, doc_list, unavailable, gap_lo=gap_lo, gap_hi=gap_hi)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=422)

    df = pd.DataFrame(rows)
    tok = uuid.uuid4().hex
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    _csv_cache[tok] = buf.getvalue()
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
    txt = _csv_cache.get(tok)
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
        "gap_lo": survey["gap_lo"],
        "gap_hi": survey["gap_hi"],
        "created_at": survey["created_at"],
        "weeks": _build_weeks(survey["year"], survey["month"]),
    }


@app.post("/api/surveys")
async def create_survey(
    title: str = Form(...),
    year: int = Form(...),
    month: int = Form(...),
    docs: str = Form(...),
    gap_lo: int = Form(5),
    gap_hi: int = Form(8),
):
    doc_list = [d.strip() for d in docs.split(",") if d.strip()]
    if not doc_list:
        raise HTTPException(status_code=422, detail="医師名を1名以上入力してください。")
    survey_id = uuid.uuid4().hex[:12]
    db.create_survey(survey_id, title.strip() or f"{year}年{month}月", year, month, doc_list, gap_lo, gap_hi)
    return JSONResponse({"id": survey_id})


@app.get("/api/surveys")
async def list_surveys():
    return JSONResponse({"surveys": db.list_surveys()})


@app.get("/api/surveys/{survey_id}")
async def get_survey(survey_id: str):
    survey = db.get_survey(survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="アンケートが見つかりません。")
    return JSONResponse(_survey_public(survey))


@app.delete("/api/surveys/{survey_id}")
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


@app.get("/api/surveys/{survey_id}/results")
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
