import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import UploadPage from './pages/UploadPage'
import AgentsPage from './pages/AgentsPage'
import InteractionView from './pages/InteractionView'
import ResultsPage from './pages/ResultsPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/agents/:id?" element={<AgentsPage />} />
        <Route path="/interaction/:pairId" element={<InteractionView />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </Layout>
  )
}
