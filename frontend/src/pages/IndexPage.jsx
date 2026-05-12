import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

const DEFAULT_COUNT = 4

export default function IndexPage() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [docs, setDocs] = useState('')
  const [counts, setCounts] = useState({})
  const [gapLo, setGapLo] = useState(5)
  const [gapHi, setGapHi] = useState(8)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const docList = useMemo(
    () => docs.split(',').map(d => d.trim()).filter(Boolean),
    [docs],
  )

  function setCount(name, value) {
    setCounts(prev => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    const countsPayload = {}
    for (const d of docList) {
      const v = counts[d]
      const n = v === '' || v === undefined ? DEFAULT_COUNT : Number(v)
      if (!Number.isInteger(n) || n < 0) {
        setError(`${d} の当直回数は 0 以上の整数で入力してください。`)
        setLoading(false)
        return
      }
      countsPayload[d] = n
    }
    const form = new FormData()
    form.append('year', year)
    form.append('month', month)
    form.append('docs', docs)
    form.append('gap_lo', gapLo)
    form.append('gap_hi', gapHi)
    form.append('counts', JSON.stringify(countsPayload))
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
        {docList.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <p style={{ margin: '4px 0', fontWeight: 'bold' }}>各医師の当直回数:</p>
            <table style={{ borderCollapse: 'collapse' }}>
              <tbody>
                {docList.map(d => (
                  <tr key={d}>
                    <td style={{ padding: '2px 8px' }}>{d}</td>
                    <td style={{ padding: '2px 8px' }}>
                      <input
                        type="number"
                        min={0}
                        max={30}
                        value={counts[d] ?? DEFAULT_COUNT}
                        onChange={e => setCount(d, e.target.value)}
                        style={{ width: 60 }}
                      />
                      回
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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
