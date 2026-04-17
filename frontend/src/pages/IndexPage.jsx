import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

export default function IndexPage() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [docs, setDocs] = useState('')
  const [gapLo, setGapLo] = useState(5)
  const [gapHi, setGapHi] = useState(8)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const form = new FormData()
    form.append('year', year)
    form.append('month', month)
    form.append('docs', docs)
    form.append('gap_lo', gapLo)
    form.append('gap_hi', gapHi)
    try {
      const res = await fetch('/api/calendar', { method: 'POST', body: form })
      const data = await res.json()
      navigate('/calendar', { state: data })
    } catch (err) {
      setError('エラーが発生しました: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>当直スケジューラ</h1>
      <p><Link to="/admin">▶ アンケート管理画面へ</Link></p>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <label>
          年:
          <input
            type="number"
            value={year}
            onChange={e => setYear(e.target.value)}
            style={{ width: 80 }}
            required
          />
        </label>{' '}
        <label>
          月:
          <input
            type="number"
            value={month}
            onChange={e => setMonth(e.target.value)}
            style={{ width: 60 }}
            required
          />
        </label>{' '}
        <label>
          医師名(カンマ区切り):
          <input
            value={docs}
            onChange={e => setDocs(e.target.value)}
            size={40}
            required
          />
        </label>
        <br />
        <label>
          シフト間隔 最小:
          <input
            type="number"
            value={gapLo}
            onChange={e => setGapLo(e.target.value)}
            style={{ width: 60 }}
            min={1}
            max={30}
            required
          />
          日
        </label>{' '}
        <label>
          最大:
          <input
            type="number"
            value={gapHi}
            onChange={e => setGapHi(e.target.value)}
            style={{ width: 60 }}
            min={1}
            max={30}
            required
          />
          日
        </label>
        <br />
        <button type="submit" disabled={loading}>
          {loading ? '読み込み中...' : 'カレンダー表示'}
        </button>
      </form>
    </div>
  )
}
