import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

const WEEKDAY_LABELS = ['日', '月', '火', '水', '木', '金', '土']

export default function AdminResultsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)
  const [gapLo, setGapLo] = useState(null)
  const [gapHi, setGapHi] = useState(null)
  const [scheduleError, setScheduleError] = useState('')

  useEffect(() => {
    (async () => {
      const res = await fetch(`/api/surveys/${id}/results`)
      if (!res.ok) {
        setError('アンケートが見つかりません')
        return
      }
      const json = await res.json()
      setData(json)
      setGapLo(json.survey.gap_lo)
      setGapHi(json.survey.gap_hi)
    })()
  }, [id])

  if (error) return <div><p className="error">{error}</p><Link to="/admin">← 管理画面へ</Link></div>
  if (!data) return <div>読み込み中...</div>

  const { survey, responses, pending } = data
  const { year, month, docs, weeks } = survey

  // 集計: dateKey|tag -> [doctor,...]
  const agg = {}
  for (const r of responses) {
    for (const item of r.blocked) {
      agg[item] = agg[item] || []
      agg[item].push(r.doctor)
    }
  }

  function cellClass(day) {
    if (!day.in_month) return ''
    if (day.is_holiday) return 'holiday'
    if (day.weekday === 6) return 'sun'
    if (day.weekday === 5) return 'sat'
    return ''
  }

  function isWeekday(day) {
    return !day.is_holiday && day.weekday !== 5 && day.weekday !== 6
  }

  function blockedFor(date, tag) {
    return agg[`${date}|${tag}`] || []
  }

  async function generateSchedule() {
    setGenerating(true)
    setScheduleError('')
    const unavailParts = []
    for (const r of responses) {
      for (const item of r.blocked) {
        unavailParts.push(`${r.doctor}|${item}`)
      }
    }
    const form = new FormData()
    form.append('year', year)
    form.append('month', month)
    form.append('docs', docs.join(','))
    form.append('unavail', unavailParts.join(','))
    form.append('gap_lo', gapLo)
    form.append('gap_hi', gapHi)
    try {
      const res = await fetch('/api/schedule', { method: 'POST', body: form })
      const d = await res.json()
      if (d.error) {
        setScheduleError(d.error)
      } else {
        navigate('/schedule', { state: d })
      }
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div>
      <p><Link to="/admin">← 管理画面へ</Link></p>
      <h2>{survey.title} - 集計結果</h2>
      <p>
        回答: {responses.length} / {docs.length}名
        {pending.length > 0 && (
          <span style={{ color: '#999' }}>（未回答: {pending.join(', ')}）</span>
        )}
      </p>

      <h3>カレンダー (入れないと申告された人数)</h3>
      <table className="cal">
        <thead>
          <tr>{WEEKDAY_LABELS.map(l => <th key={l}>{l}</th>)}</tr>
        </thead>
        <tbody>
          {weeks.map((week, wi) => (
            <tr key={wi}>
              {week.map((day, di) => {
                const dayBlocked = day.in_month ? blockedFor(day.date, 'DAY') : []
                const nightBlocked = day.in_month ? blockedFor(day.date, 'NIGHT') : []
                return (
                  <td key={di} className={cellClass(day)}>
                    {day.in_month && (
                      <div className="cell-inner">
                        <span className="day-num">{day.day}</span>
                        <div style={{ fontSize: '0.7em', textAlign: 'left', width: '100%' }}>
                          {!isWeekday(day) && dayBlocked.length > 0 && (
                            <div title={dayBlocked.join(', ')} style={{ color: '#d9534f' }}>
                              昼×{dayBlocked.length}
                            </div>
                          )}
                          {nightBlocked.length > 0 && (
                            <div title={nightBlocked.join(', ')} style={{ color: '#0275d8' }}>
                              夜×{nightBlocked.length}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>

      <h3>回答詳細</h3>
      <table className="schedule-table">
        <thead>
          <tr><th>医師</th><th>入れないシフト</th><th>送信日時 (UTC)</th></tr>
        </thead>
        <tbody>
          {responses.map(r => (
            <tr key={r.doctor}>
              <td>{r.doctor}</td>
              <td>
                {r.blocked.length === 0
                  ? <span style={{ color: '#999' }}>なし</span>
                  : r.blocked.map(b => {
                      const [d, t] = b.split('|')
                      return <span key={b} style={{ marginRight: 6 }}>
                        {d} ({t === 'DAY' ? '昼' : '夜'})
                      </span>
                    })}
              </td>
              <td>{r.submitted_at}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <label>シフト間隔 最小:
            <input type="number" min={1} max={30} value={gapLo ?? ''} onChange={e => setGapLo(Number(e.target.value))}
              style={{ width: 60, marginLeft: 4, marginRight: 16 }} />
          </label>
          <label>最大:
            <input type="number" min={1} max={30} value={gapHi ?? ''} onChange={e => setGapHi(Number(e.target.value))}
              style={{ width: 60, marginLeft: 4 }} />
          </label>
        </div>
        {scheduleError && (
          <p className="error" style={{ margin: 0 }}>
            {scheduleError}　※上記の間隔を変更して再度お試しください。
          </p>
        )}
        <button type="button" disabled={generating} onClick={generateSchedule}>
          {generating ? '作成中...' : 'この結果でシフト作成'}
        </button>
      </div>
    </div>
  )
}
