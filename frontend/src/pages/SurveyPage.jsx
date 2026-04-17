import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

const WEEKDAY_LABELS = ['日', '月', '火', '水', '木', '金', '土']

export default function SurveyPage() {
  const { id } = useParams()
  const [survey, setSurvey] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [doctor, setDoctor] = useState('')
  const [blocked, setBlocked] = useState(new Set())
  const [existing, setExisting] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    (async () => {
      const res = await fetch(`/api/surveys/${id}`)
      if (!res.ok) {
        setLoadError('アンケートが見つかりません。URLをご確認ください。')
        return
      }
      const data = await res.json()
      setSurvey(data)
      if (data.docs?.length) setDoctor(data.docs[0])
    })()
  }, [id])

  useEffect(() => {
    if (!survey || !doctor) return
    setExisting(null)
    setBlocked(new Set())
    setSubmitted(false);
    (async () => {
      const res = await fetch(`/api/surveys/${id}/responses/${encodeURIComponent(doctor)}`)
      if (!res.ok) return
      const data = await res.json()
      if (data.response) {
        setExisting(data.response)
        setBlocked(new Set(data.response.blocked))
      }
    })()
  }, [survey, doctor, id])

  if (loadError) return <div><h1>当直アンケート</h1><p className="error">{loadError}</p></div>
  if (!survey) return <div>読み込み中...</div>

  const { year, month, docs, weeks, title } = survey

  function key(date, tag) { return `${date}|${tag}` }

  function toggle(date, tag) {
    const k = key(date, tag)
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
    setSubmitting(true)
    setError('')
    const form = new FormData()
    form.append('doctor', doctor)
    form.append('blocked', [...blocked].join(','))
    try {
      const res = await fetch(`/api/surveys/${id}/responses`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'エラーが発生しました')
      }
      setSubmitted(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1>{title}</h1>
      <p>対象: {year}年{month}月</p>
      <p>自分の名前を選び、入れない日付の「昼」または「夜」ボタンを押してください。</p>

      <form onSubmit={handleSubmit}>
        <label>
          医師名:{' '}
          <select value={doctor} onChange={e => setDoctor(e.target.value)}>
            {docs.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        {existing && (
          <p style={{ color: '#666' }}>
            前回送信: {existing.submitted_at} (UTC) — 上書きする場合は再送信してください。
          </p>
        )}

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
                              className={`shift-btn day-btn${blocked.has(key(day.date, 'DAY')) ? ' active' : ''}`}
                              onClick={() => toggle(day.date, 'DAY')}
                            >昼</button>
                          )}
                          <button
                            type="button"
                            className={`shift-btn night-btn${blocked.has(key(day.date, 'NIGHT')) ? ' active' : ''}`}
                            onClick={() => toggle(day.date, 'NIGHT')}
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

        {error && <p className="error">{error}</p>}
        {submitted && <p style={{ color: 'green' }}>送信しました。ありがとうございました！</p>}

        <button type="submit" disabled={submitting} style={{ marginTop: 15 }}>
          {submitting ? '送信中...' : (existing ? '上書き送信' : '送信')}
        </button>
      </form>
    </div>
  )
}
