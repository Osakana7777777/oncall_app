import io
import uuid
import calendar
import datetime as _dt
from typing import Dict, List, Set

import pandas as pd
from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse, JSONResponse

from .holiday_utils import is_holiday
from .scheduler import make_schedule

app = FastAPI(title="当直スケジューラ")

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
    return JSONResponse({
        "year": year,
        "month": month,
        "rows": rows,
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
