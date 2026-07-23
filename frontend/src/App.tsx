import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import ManualInput from './pages/ManualInput'
import PestScan from './pages/PestScan'
import History from './pages/History'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="flex-1 flex flex-col">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/manual-input" element={<ManualInput />} />
            <Route path="/pest-scan" element={<PestScan />} />
            <Route path="/history" element={<History />} />
          </Route>
        </Routes>
      </main>
    </BrowserRouter>
  )
}
