import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import { theme } from './theme'

// Pages
import Login from './pages/Login'
import Register from './pages/Register'
import CreateProduct from './pages/CreateProduct'
import LiveCreation from './pages/LiveCreation'
import Dashboard from './pages/Dashboard'
import ProjectDetail from './pages/ProjectDetail'
import LandingFlow from './pages/LandingFlow'
import FaibricAdmin from './pages/FaibricAdmin'
import CustomerDashboard from './pages/CustomerDashboard'
import AdminPanelBuilder from './pages/AdminPanelBuilder'
import ServiceStatus from './pages/ServiceStatus'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingFlow />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Routes - Full Screen */}
          <Route element={<ProtectedRoute />}>
            <Route path="/create" element={<CreateProduct />} />
            <Route path="/create/:id" element={<LiveCreation />} />
            <Route path="/live-creation/:id" element={<LiveCreation />} />
          </Route>
            
          {/* Protected Routes - With Layout */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/projects/:id" element={<ProjectDetail />} />
              <Route path="/account" element={<CustomerDashboard />} />
              <Route path="/panel-builder" element={<AdminPanelBuilder />} />
            </Route>
          </Route>

          {/* Faibric Admin (Staff Only) */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/admin" element={<FaibricAdmin />} />
              <Route path="/admin/services" element={<ServiceStatus />} />
            </Route>
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  )
}

export default App
