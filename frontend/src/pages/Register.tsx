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
  Grid,
} from '@mui/material'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store'
import { setUser, setLoading, setError } from '../features/auth/authSlice'
import { authService } from '../services/auth'

const Register = () => {
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { loading } = useSelector((state: RootState) => state.auth)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password2: '',
    first_name: '',
    last_name: '',
  })
  const [error, setErrorMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage('')

    if (formData.password !== formData.password2) {
      setErrorMessage('Passwords do not match')
      return
    }

    dispatch(setLoading(true))

    try {
      const response = await authService.register(formData)
      dispatch(setUser(response.user))
      dispatch(setLoading(false))
      navigate('/dashboard')
    } catch (err: any) {
      dispatch(setLoading(false))
      const errorData = err.response?.data
      if (errorData) {
        const errorMsg = Object.entries(errorData)
          .map(([key, value]) => `${key}: ${value}`)
          .join(', ')
        setErrorMessage(errorMsg)
      } else {
        setErrorMessage(err.message || 'Registration failed')
      }
      dispatch(setError(err.message || 'Registration failed'))
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: '#ffffff', display: 'flex', alignItems: 'center', py: 4 }}>
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
              Register
            </Typography>
            <Typography variant="body2" align="center" sx={{ color: '#374151', mb: 3 }}>
              Create your Faibric account
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
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
                value={formData.email}
                onChange={handleChange}
              />
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    margin="normal"
                    fullWidth
                    id="first_name"
                    label="First Name"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleChange}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    margin="normal"
                    fullWidth
                    id="last_name"
                    label="Last Name"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleChange}
                  />
                </Grid>
              </Grid>
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type="password"
                id="password"
                autoComplete="new-password"
                value={formData.password}
                onChange={handleChange}
              />
              <TextField
                margin="normal"
                required
                fullWidth
                name="password2"
                label="Confirm Password"
                type="password"
                id="password2"
                value={formData.password2}
                onChange={handleChange}
              />
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ mt: 3, mb: 2 }}
                disabled={loading}
              >
                {loading ? 'Creating Account...' : 'Sign Up'}
              </Button>
              <Box sx={{ textAlign: 'center' }}>
                <Link to="/login" style={{ textDecoration: 'none' }}>
                  <Typography variant="body2" sx={{ color: '#2563eb' }}>
                    Already have an account? Sign In
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

export default Register
