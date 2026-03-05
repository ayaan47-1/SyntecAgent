import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ChatInterface from './ChatInterface'
import ErrorBoundary from './ErrorBoundary'
import SyntecChatWidget from './SyntecChatWidget'

export default function App() {
  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          <Route path="/" element={<ChatInterface />} />
          <Route path="/widget" element={<SyntecChatWidget />} />
        </Routes>
      </Router>
    </ErrorBoundary>
  )
}
