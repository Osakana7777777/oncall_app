import io
import uuid
import calendar
import datetime as _dt
from typing import Dict, List, Set

import pandas as pd
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, StreamingResponse

from .holiday_utils import is_holiday, jpholiday
from .scheduler import make_schedule
from .templates import CSS, CAL_JS_T, INDEX_T, CAL_T, SCHED_T

app = FastAPI(title="当直スケジューラ")

_csv_cache: Dict[str, str] = {}


def cal_html(y: int, m: int, docs: List[str], unavail: str, gap_lo: int = 5, gap_hi: int = 8, error: str = ""):
    weeks = list(calendar.Calendar(firstweekday=6).monthdatescalendar(y, m))
    js = CAL_JS_T.render(init=unavail)
    return CAL_T.render(
        css=CSS,
        y=y,
        m=m,
        docs=docs,
        unavail=unavail,
        gap_lo=gap_lo,
        gap_hi=gap_hi,
        weeks=weeks,
        holiday=is_holiday,
        error=error,
        js=js,
    )


@app.get("/", response_class=HTMLResponse)
async def index():
    today = _dt.date.today()
    return HTMLResponse(
        INDEX_T.render(
            css=CSS,
            y=today.year,
            m=today.month,
            docs="",
            gap_lo=5,
            gap_hi=8,
            mode="jpholiday" if jpholiday else "週末のみ",
        )
    )


@app.post("/calendar", response_class=HTMLResponse)
async def show_calendar(
    year: int = Form(...), month: int = Form(...), docs: str = Form(...),
    gap_lo: int = Form(...), gap_hi: int = Form(...)
):
    y, m = int(year), int(month)
    doc_list = [d.strip() for d in docs.split(",") if d.strip()]
    return HTMLResponse(cal_html(y, m, doc_list, unavail="", gap_lo=gap_lo, gap_hi=gap_hi))


@app.post("/schedule", response_class=HTMLResponse)
async def schedule_route(
    year: int = Form(...),
    month: int = Form(...),
    docs: str = Form(...),
    unavail: str = Form(""),
    gap_lo: int = Form(...),
    gap_hi: int = Form(...),
):
    y, m = int(year), int(month)
    doc_list = [d.strip() for d in docs.split(",") if d.strip()]
    # unavailable 解析
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
        rows = make_schedule(y, m, doc_list, unavailable, gap_lo=gap_lo, gap_hi=gap_hi)
    except Exception as e:
        return HTMLResponse(cal_html(y, m, doc_list, unavail, gap_lo, gap_hi, str(e)))

    df = pd.DataFrame(rows)
    tok = uuid.uuid4().hex
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    _csv_cache[tok] = buf.getvalue()
    return HTMLResponse(SCHED_T.render(css=CSS, y=y, m=m, rows=rows, tok=tok))


@app.get("/csv", response_class=StreamingResponse)
async def download_csv(tok: str):
    txt = _csv_cache.get(tok)
    if txt is None:
        return HTMLResponse("<h3>リンクが無効です。</h3>")
    # UTF-8-SIG で送信
    return StreamingResponse(
        io.BytesIO(txt.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shift.csv"},
    )