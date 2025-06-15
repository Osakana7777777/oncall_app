# oncall_app.py  (FastAPI 版・日直/宿直別クリック・入力保持付き)
# ------------------------------------------------------------
#  起動例:
#     pip install fastapi uvicorn jinja2 pandas jpholiday
#     uvicorn oncall_app:app --reload
#  ブラウザで http://localhost:8000
# ------------------------------------------------------------
from __future__ import annotations
import random, collections, calendar, io, uuid, datetime as _dt
from typing import List, Dict, Set

# ===== 祝日判定 ============================================================
try:
    import jpholiday
    def is_holiday(day: _dt.date) -> bool: return jpholiday.is_holiday(day)
except ImportError:
    jpholiday = None
    def is_holiday(day: _dt.date) -> bool: return False

# ===== シフト定義 ==========================================================
SHIFT_JP   = {"WE_DAY":"休日 日直", "WE_NIGHT":"休日 宿直", "WD_NIGHT":"平日 宿直"}
SHIFT_PRIO = {k:i for i,k in enumerate(["WE_DAY","WE_NIGHT","WD_NIGHT"])}
REQUIRED   = {"WE_DAY":1, "WE_NIGHT":1, "WD_NIGHT":2}

# ===== スロット作成 ========================================================
def generate_shift_slots(year:int, month:int):
    cal   = calendar.Calendar(firstweekday=6)            # Sun-start
    slots = []
    for d in cal.itermonthdates(year, month):
        if d.month!=month: continue
        if d.weekday()>=5 or is_holiday(d):               # 休日
            slots += [(d,"WE_DAY"), (d,"WE_NIGHT")]
        else:                                             # 平日
            slots.append((d,"WD_NIGHT"))
    return sorted(slots, key=lambda x:(SHIFT_PRIO[x[1]],x[0]))

# ===== 間隔チェック ========================================================
def ok_gap(seq, lo=5, hi=8):
    seq=sorted(seq)
    return all(lo <= (seq[i+1]-seq[i]).days <= hi for i in range(len(seq)-1))

# ===== スケジューラ ========================================================
def make_schedule(year:int, month:int, doctors:List[str],
                  unavailable:Dict[str,Set[tuple]], attempts=30000, seed=42):
    random.seed(seed)
    for d in doctors: unavailable.setdefault(d,set())

    slots = generate_shift_slots(year, month)
    avail = {tp:[d for d,t in slots if t==tp] for tp in REQUIRED}
    if any(collections.Counter(t for _,t in slots)[tp] < REQUIRED[tp]*len(doctors)
           for tp in REQUIRED):
        raise RuntimeError("この月はシフト枠が不足しています。")

    def try_once():
        pool = {k:v[:] for k,v in avail.items()}
        for v in pool.values(): random.shuffle(v)
        assign={}
        for doc in random.sample(doctors,len(doctors)):
            picks=[]
            # 休日: 日直→宿直
            for typ in ["WE_DAY","WE_NIGHT"]:
                cand=[d for d in pool[typ] if (d,typ) not in unavailable[doc] and ok_gap(picks+[d])]
                if not cand: return None
                c=random.choice(cand); picks.append(c); pool[typ].remove(c)
            # 平日宿直2
            wds=[d for d in pool["WD_NIGHT"] if (d,"WD_NIGHT") not in unavailable[doc]]
            random.shuffle(wds)
            success=False
            for i in range(len(wds)):
                for j in range(i+1,len(wds)):
                    seq=picks+[wds[i],wds[j]]
                    if ok_gap(seq): picks+=[wds[i],wds[j]]; pool["WD_NIGHT"].remove(wds[i]); pool["WD_NIGHT"].remove(wds[j]); success=True; break
                if success: break
            if not success: return None
            assign[doc]=list(zip(picks,["WE_DAY","WE_NIGHT","WD_NIGHT","WD_NIGHT"]))
        return sorted(
            [{"Date":d,"Shift":SHIFT_JP[tp],"Doctor":doc} for doc,l in assign.items() for d,tp in l],
            key=lambda r:(r["Date"], r["Shift"]))
    for _ in range(attempts):
        res=try_once()
        if res: return res
    raise RuntimeError("条件を満たす組み合わせが見つかりませんでした。")

# ===========================================================================
# FastAPI アプリ
# ===========================================================================
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from jinja2 import Template
import pandas as pd
app=FastAPI(title="当直スケジューラ")

# ---------- 共通 CSS -------------------------------------------------------
CSS = """
body{font-family:sans-serif;margin:20px;line-height:1.45}
.cal{border-collapse:collapse}
.cal td{width:60px;height:60px;text-align:center;cursor:pointer;position:relative;vertical-align:top}
.cal .part{position:absolute;left:0;right:0;height:50%;line-height:28px;font-size:.8em}
.cal .dayPart{top:0;border-bottom:1px solid #ccc}
.cal .nightPart{bottom:0}
.dayMark{color:#d9534f}
.nightMark{color:#0275d8}
.sat{border:2px solid #007bff}
.sun{border:2px solid #dc3545}
.holiday{border:2px solid #28a745}
"""

# ---------- JS (unavail_init はテンプレートで差し込み) ----------------------
CAL_JS = Template("""
const blocked=new Set("{{unavail_init}}".split(',').filter(Boolean));
function docSel(){return document.getElementById('docSel').value;}
function key(doc,date,tag){return doc+'|'+date+'|'+tag;}
function toggle(date,tag){const k=key(docSel(),date,tag);blocked.has(k)?blocked.delete(k):blocked.add(k);render();}
function render(){const doc=docSel();
 document.querySelectorAll('.cal td[data-date]').forEach(td=>{
   const date=td.dataset.date,
         dayK=key(doc,date,'DAY'),
         nightK=key(doc,date,'NIGHT');
   td.querySelector('.dayPart').innerHTML=blocked.has(dayK)?'<span class="dayMark">日</span>':'';
   td.querySelector('.nightPart').innerHTML=blocked.has(nightK)?'<span class="nightMark">夜</span>':'';
 });
 document.getElementById('unavail').value=[...blocked].join(',');
}
document.addEventListener('DOMContentLoaded',()=>{document.getElementById('docSel').addEventListener('change',render);render();});
""")

# ---------- HTML テンプレート ----------------------------------------------
INDEX_T = Template("""
<!doctype html><html><head><meta charset="utf-8"><title>当直スケジューラ</title>
<style>{{css}}</style></head><body>
<h1>当直スケジューラ</h1>
<form method="post" action="/calendar">
 年:<input type="number" name="year" value="{{y}}" style="width:80px" required>
 月:<input type="number" name="month" value="{{m}}" style="width:60px" required>
 医師名(カンマ区切り):<input name="docs" size="40" required value="{{docs}}">
 <button type="submit">カレンダー表示</button>
</form>
<p>休日判定: {{mode}}</p>
</body></html>
""")

CAL_T = Template("""
<!doctype html><html><head><meta charset="utf-8"><title>カレンダー</title>
<style>{{css}}</style></head><body>
{% if error %}<p style="color:red">{{error}}</p>{% endif %}
<h2>{{y}}年{{m}}月 入れないシフトを選択</h2>
<form method="post" action="/schedule">
 <input type="hidden" name="year" value="{{y}}"><input type="hidden" name="month" value="{{m}}">
 <input type="hidden" name="docs" value="{{docs|join(',')}}">
 <input type="hidden" name="unavail" id="unavail" value="{{unavail}}">
 医師:<select id="docSel">{% for d in docs %}<option value="{{d}}">{{d}}</option>{% endfor %}</select>
 <table class="cal">
  <tr><th>日</th><th>月</th><th>火</th><th>水</th><th>木</th><th>金</th><th>土</th></tr>
  {% for week in weeks %}<tr>{% for day in week %}
    {% if day.month==m %}
      {% set cls= day.weekday()==5 and 'sat' or day.weekday()==6 and 'sun' or '' %}
      {% if holiday(day) %}{% set cls='holiday' %}{% endif %}
      <td data-date="{{day}}" class="{{cls}}">
        <div class="part dayPart"  onclick="event.stopPropagation();toggle('{{day}}','DAY')"></div>
        <div class="part nightPart" onclick="event.stopPropagation();toggle('{{day}}','NIGHT')"></div>
        {{day.day}}
      </td>
    {% else %}<td></td>{% endif %}{% endfor %}</tr>{% endfor %}
 </table>
 <button type="submit" style="margin-top:15px">スケジュール作成</button>
</form>
<script>{{js}}</script>
</body></html>
""")

SCHED_T = Template("""
<!doctype html><html><head><meta charset="utf-8"><title>シフト表</title>
<style>{{css}}</style></head><body>
<h2>{{y}}年{{m}}月 シフト表</h2>
<p><a href="/csv?tok={{tok}}">CSV ダウンロード</a></p>
<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse">
<tr><th>日付</th><th>シフト</th><th>医師</th></tr>
{% for r in rows %}<tr><td>{{r['Date']}}</td><td>{{r['Shift']}}</td><td>{{r['Doctor']}}</td></tr>{% endfor %}
</table>
</body></html>
""")

# ---------- CSV cache ------------------------------------------------------
_csv_cache: Dict[str,str] = {}

# ---------- 共通レンダリング関数 -----------------------------------------
def calendar_page_html(y:int,m:int,docs:List[str],unavail:str,error:str=""):
    cal = calendar.Calendar(firstweekday=6)
    weeks = list(cal.monthdatescalendar(y,m))
    return CAL_T.render(
        css=CSS, js=CAL_JS.render(unavail_init=unavail),
        y=y, m=m, docs=docs, weeks=weeks, unavail=unavail,
        error=error, holiday=is_holiday)

# ---------- Routes ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    today=_dt.date.today()
    return HTMLResponse(INDEX_T.render(css=CSS,y=today.year,m=today.month,docs="",mode="jpholiday" if jpholiday else "週末のみ"))

@app.post("/calendar", response_class=HTMLResponse)
async def show_calendar(year:int=Form(...), month:int=Form(...), docs:str=Form(...)):
    y,m=int(year),int(month)
    doc_list=[d.strip() for d in docs.split(',') if d.strip()]
    return HTMLResponse(calendar_page_html(y,m,doc_list,unavail=""))

@app.post("/schedule", response_class=HTMLResponse)
async def make_schedule_route(year:int=Form(...), month:int=Form(...), docs:str=Form(...), unavail:str=Form("")):
    y,m=int(year),int(month)
    doc_list=[d.strip() for d in docs.split(',') if d.strip()]
    # unavailable 解析
    unavailable:Dict[str,Set[tuple]]={d:set() for d in doc_list}
    if unavail:
        for item in unavail.split(','):
            if not item: continue
            doc,date_str,tag=item.split('|')
            dt=_dt.date.fromisoformat(date_str)
            if tag=="DAY":
                if dt.weekday()>=5 or is_holiday(dt):
                    unavailable[doc].add((dt,"WE_DAY"))
            else:  # NIGHT
                if dt.weekday()>=5 or is_holiday(dt):
                    unavailable[doc].add((dt,"WE_NIGHT"))
                else:
                    unavailable[doc].add((dt,"WD_NIGHT"))
    # 生成
    try:
        rows=make_schedule(y,m,doc_list,unavailable)
    except Exception as e:
        # エラー: カレンダーへ戻す
        return HTMLResponse(calendar_page_html(y,m,doc_list,unavail,str(e)))

    df=pd.DataFrame(rows)
    tok=uuid.uuid4().hex
    buf=io.StringIO(); df.to_csv(buf,index=False)
    _csv_cache[tok]=buf.getvalue()
    return HTMLResponse(SCHED_T.render(css=CSS,y=y,m=m,rows=rows,tok=tok))

@app.get("/csv", response_class=StreamingResponse)
async def download_csv(tok: str):
    txt = _csv_cache.get(tok)
    if txt is None:
        return HTMLResponse("<h3>リンクが無効です。</h3>")

    # ── ここで BOM 付き UTF-8 にエンコード ──
    csv_bytes = txt.encode("utf-8-sig")          # ★ポイント

    return StreamingResponse(
        io.BytesIO(csv_bytes),                   # バイト列をストリーム化
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shift.csv"}
    )