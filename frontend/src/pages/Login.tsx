import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
} from '@mui/material'
import { useDispatch } from 'react-redux'
import { setUser, setLoading, setError } from '../features/auth/authSlice'
import { authService } from '../services/auth'

const Login = () => {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  })
  const [error, setErrorMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage('')
    dispatch(setLoading(true))

    try {
      const response = await authService.login(formData)
      dispatch(setUser(response.user))
      dispatch(setLoading(false))
      navigate('/dashboard')
    } catch (err: any) {
      dispatch(setLoading(false))
      setErrorMessage(err.response?.data?.detail || 'Login failed')
      dispatch(setError(err.message || 'Login failed'))
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#ffffff', display: 'flex', alignItems: 'center' }}>
      <Container maxWidth="sm">
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Paper elevation={0} sx={{ p: 4, width: '100%', border: '1px solid #e5e7eb' }}>
            <Typography component="h1" variant="h4" align="center" sx={{ color: '#000000', fontWeight: 700, mb: 1 }}>
              Login
            </Typography>
            <Typography variant="body2" align="center" sx={{ color: '#374151', mb: 3 }}>
              Sign in to your Faibric account
            </Typography>
            
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
              <TextField
                margin="normal"
                required
                fullWidth
                id="username"
                label="Username"
                name="username"
                autoComplete="username"
                autoFocus
                value={formData.username}
                onChange={handleChange}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type="password"
                id="password"
                autoComplete="current-password"
                value={formData.password}
                onChange={handleChange}
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
              >
                Sign In
              </Button>
              <Box sx={{ textAlign: 'center' }}>
                <Link to="/register" style={{ textDecoration: 'none' }}>
                  <Typography variant="body2" sx={{ color: '#2563eb' }}>
                    Don't have an account? Sign Up
                  </Typography>
                </Link>
              </Box>
            </Box>
          </Paper>
        </Box>
      </Container>
    </Box>
  )
}

export default Login
