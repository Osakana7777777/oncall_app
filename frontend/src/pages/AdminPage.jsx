import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

const DEFAULT_COUNT = 4

export default function AdminPage() {
  const today = new Date()
  const [surveys, setSurveys] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [title, setTitle] = useState('')
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [docs, setDocs] = useState('')
  const [counts, setCounts] = useState({})
  const [gapLo, setGapLo] = useState(5)
  const [gapHi, setGapHi] = useState(8)

  const docList = useMemo(
    () => docs.split(',').map(d => d.trim()).filter(Boolean),
    [docs],
  )

  function setCount(name, value) {
    setCounts(prev => ({ ...prev, [name]: value }))
  }

  async function refresh() {
    const res = await fetch('/api/surveys')
    const data = await res.json()
    setSurveys(data.surveys || [])
  }

  useEffect(() => { refresh() }, [])

  async function handleCreate(e) {
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
    form.append('title', title || `${year}年${month}月`)
    form.append('year', year)
    form.append('month', month)
    form.append('docs', docs)
    form.append('gap_lo', gapLo)
    form.append('gap_hi', gapHi)
    form.append('counts', JSON.stringify(countsPayload))
    try {
      const res = await fetch('/api/surveys', { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'エラーが発生しました')
      }
      setTitle('')
      setDocs('')
      setCounts({})
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id) {
    if (!confirm('このアンケートを削除しますか?')) return
    await fetch(`/api/surveys/${id}`, { method: 'DELETE' })
    await refresh()
  }

  function surveyUrl(id) {
    return `${window.location.origin}/survey/${id}`
  }

  async function copyUrl(id) {
    try {
      await navigator.clipboard.writeText(surveyUrl(id))
      alert('URLをコピーしました')
    } catch {
      prompt('このURLをコピーしてください', surveyUrl(id))
    }
  }

  return (
    <div>
      <p><Link to="/">← トップへ</Link></p>
      <h1>管理画面 (アンケート)</h1>

      <section style={{ border: '1px solid #ccc', padding: 12, marginBottom: 20 }}>
        <h2>新しいアンケートを作成</h2>
        {error && <p className="error">{error}</p>}
        <form onSubmit={handleCreate}>
          <div>
            <label>タイトル:
              <input value={title} onChange={e => setTitle(e.target.value)} size={30} placeholder="(省略時は年月)" />
            </label>
          </div>
          <div>
            <label>年:
              <input type="number" value={year} onChange={e => setYear(e.target.value)} style={{ width: 80 }} required />
            </label>{' '}
            <label>月:
              <input type="number" value={month} onChange={e => setMonth(e.target.value)} style={{ width: 60 }} required />
            </label>
          </div>
          <div>
            <label>医師名 (カンマ区切り):
              <input value={docs} onChange={e => setDocs(e.target.value)} size={40} required />
            </label>
          </div>
          {docList.length > 0 && (
            <div style={{ marginTop: 8 }}>
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
          <div style={{ marginTop: 8 }}>
            <label>シフト間隔 最小:
              <input type="number" value={gapLo} onChange={e => setGapLo(e.target.value)} style={{ width: 60 }} min={1} max={30} required />
            </label>{' '}
            <label>最大:
              <input type="number" value={gapHi} onChange={e => setGapHi(e.target.value)} style={{ width: 60 }} min={1} max={30} required />
            </label>
          </div>
          <button type="submit" disabled={loading}>
            {loading ? '作成中...' : 'アンケート作成'}
          </button>
        </form>
      </section>

      <section>
        <h2>アンケート一覧</h2>
        {surveys.length === 0 && <p>まだアンケートはありません。</p>}
        <table className="schedule-table">
          <thead>
            <tr>
              <th>タイトル</th>
              <th>対象月</th>
              <th>医師</th>
              <th>回答数</th>
              <th>共有URL</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {surveys.map(s => (
              <tr key={s.id}>
                <td>{s.title}</td>
                <td>{s.year}/{s.month}</td>
                <td>{s.docs.length}名</td>
                <td>{s.response_count} / {s.docs.length}</td>
                <td>
                  <code style={{ fontSize: '0.8em' }}>{surveyUrl(s.id)}</code>
                  <br />
                  <button type="button" onClick={() => copyUrl(s.id)}>URLコピー</button>
                </td>
                <td>
                  <Link to={`/admin/results/${s.id}`}>
                    <button type="button">集計</button>
                  </Link>{' '}
                  <button type="button" onClick={() => handleDelete(s.id)}>削除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
