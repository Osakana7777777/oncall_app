from jinja2 import Template

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

CAL_JS_T = Template("""
const blocked=new Set("{{init}}".split(',').filter(Boolean));
function docSel(){return document.getElementById('docSel').value;}
function key(doc,date,tag){return doc+'|'+date+'|'+tag;}
function toggle(date,tag){const k=key(docSel(),date,tag);blocked.has(k)?blocked.delete(k):blocked.add(k);render();}
function render(){const doc=docSel();
  document.querySelectorAll('.cal td[data-date]').forEach(td=>{
    const date=td.dataset.date,
          dK=key(doc,date,'DAY'),
          nK=key(doc,date,'NIGHT');
    td.querySelector('.dayPart').innerHTML=blocked.has(dK)?'<span class="dayMark">日</span>':'';
    td.querySelector('.nightPart').innerHTML=blocked.has(nK)?'<span class="nightMark">夜</span>':'';
  });
  document.getElementById('unavail').value=[...blocked].join(',');
}
document.addEventListener('DOMContentLoaded',()=>{document.getElementById('docSel').addEventListener('change',render);render();});
""")

INDEX_T = Template("""
<!doctype html><html><head><meta charset="utf-8"><title>当直スケジューラ</title>
<style>{{css}}</style></head><body>
<h1>当直スケジューラ</h1>
<form method="post" action="/calendar">
 年:<input type="number" name="year"  value="{{y}}" style="width:80px" required>
 月:<input type="number" name="month" value="{{m}}" style="width:60px" required>
 医師名(カンマ区切り):<input name="docs" size="40" required value="{{docs}}">
 <br>
 シフト間隔 最小:<input type="number" name="gap_lo" value="{{gap_lo}}" style="width:60px" min="1" max="30" required>日
 最大:<input type="number" name="gap_hi" value="{{gap_hi}}" style="width:60px" min="1" max="30" required>日
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
 <input type="hidden" name="year"  value="{{y}}"><input type="hidden" name="month" value="{{m}}">
 <input type="hidden" name="docs"  value="{{docs|join(',')}}">
 <input type="hidden" name="unavail" id="unavail" value="{{unavail}}">
 <input type="hidden" name="gap_lo" value="{{gap_lo}}">
 <input type="hidden" name="gap_hi" value="{{gap_hi}}">
 医師:<select id="docSel">{% for d in docs %}<option value="{{d}}">{{d}}</option>{% endfor %}</select>
 <table class="cal"><tr><th>日</th><th>月</th><th>火</th><th>水</th><th>木</th><th>金</th><th>土</th></tr>
 {% for w in weeks %}<tr>{% for day in w %}
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