import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

const WEEKDAY_LABELS = ['日', '月', '火', '水', '木', '金', '土']

export default function CalendarPage() {
  const { state } = useLocation()
  const navigate = useNavigate()

  const { year, month, docs, weeks, gap_lo, gap_hi } = state || {}
  const [selectedDoc, setSelectedDoc] = useState(docs?.[0] ?? '')
  const [blocked, setBlocked] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  if (!state) {
    navigate('/')
    return null
  }

  function key(doc, date, tag) {
    return `${doc}|${date}|${tag}`
  }

  function toggle(date, tag) {
    const k = key(selectedDoc, date, tag)
    setBlocked(prev => {
      const next = new Set(prev)
      next.has(k) ? next.delete(k) : next.add(k)
      return next
    })
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

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const form = new FormData()
    form.append('year', year)
    form.append('month', month)
    form.append('docs', docs.join(','))
    form.append('unavail', [...blocked].join(','))
    form.append('gap_lo', gap_lo)
    form.append('gap_hi', gap_hi)
    try {
      const res = await fetch('/api/schedule', { method: 'POST', body: form })
      const data = await res.json()
      if (data.error) {
        setError(data.error)
      } else {
        navigate('/schedule', { state: data })
      }
    } catch (err) {
      setError('エラーが発生しました: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2>{year}年{month}月 入れないシフトを選択</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          医師:{' '}
          <select value={selectedDoc} onChange={e => setSelectedDoc(e.target.value)}>
            {docs.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <table className="cal">
          <thead>
            <tr>{WEEKDAY_LABELS.map(l => <th key={l}>{l}</th>)}</tr>
          </thead>
          <tbody>
            {weeks.map((week, wi) => (
              <tr key={wi}>
                {week.map((day, di) => (
                  <td key={di} className={cellClass(day)}>
                    {day.in_month && (
                      <div className="cell-inner">
                        <span className="day-num">{day.day}</span>
                        <div className="shift-btns">
                          {!isWeekday(day) && (
                            <button
                              type="button"
                              className={`shift-btn day-btn${blocked.has(key(selectedDoc, day.date, 'DAY')) ? ' active' : ''}`}
                              onClick={e => { e.stopPropagation(); toggle(day.date, 'DAY') }}
                            >昼</button>
                          )}
                          <button
                            type="button"
                            className={`shift-btn night-btn${blocked.has(key(selectedDoc, day.date, 'NIGHT')) ? ' active' : ''}`}
                            onClick={e => { e.stopPropagation(); toggle(day.date, 'NIGHT') }}
                          >夜</button>
                        </div>
                      </div>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <br />
        <button type="submit" disabled={loading} style={{ marginTop: 15 }}>
          {loading ? '作成中...' : 'スケジュール作成'}
        </button>
      </form>
    </div>
  )
}
