import { BrowserRouter, Routes, Route } from 'react-router-dom'
import IndexPage from './pages/IndexPage'
import CalendarPage from './pages/CalendarPage'
import SchedulePage from './pages/SchedulePage'
import AdminPage from './pages/AdminPage'
import AdminResultsPage from './pages/AdminResultsPage'
import SurveyPage from './pages/SurveyPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IndexPage />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/schedule" element={<SchedulePage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/results/:id" element={<AdminResultsPage />} />
        <Route path="/survey/:id" element={<SurveyPage />} />
      </Routes>
    </BrowserRouter>
  )
}
