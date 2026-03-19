import { useLocation, useNavigate } from 'react-router-dom'

export default function SchedulePage() {
  const { state } = useLocation()
  const navigate = useNavigate()

  if (!state) {
    navigate('/')
    return null
  }

  const { year, month, rows, tok } = state

  return (
    <div>
      <h2>{year}年{month}月 シフト表</h2>
      <p><a href={`/csv?tok=${tok}`}>CSV ダウンロード</a></p>
      <table className="schedule-table">
        <thead>
          <tr>
            <th>日付</th>
            <th>シフト</th>
            <th>医師</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{r.Date}</td>
              <td>{r.Shift}</td>
              <td>{r.Doctor}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <br />
      <button onClick={() => navigate('/')}>最初に戻る</button>
    </div>
  )
}
