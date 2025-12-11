import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material'
import { useAuth } from '../hooks/useAuth'
import { useNavigate } from 'react-router-dom'

const Navbar = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <AppBar position="static" elevation={0} sx={{ bgcolor: '#ffffff', borderBottom: '1px solid #e5e7eb' }}>
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1, color: '#000000', fontWeight: 600 }}>
          Faibric
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="body2" sx={{ color: '#374151' }}>{user?.username}</Typography>
          <Button onClick={handleLogout} variant="outlined" size="small">
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  )
}

export default Navbar
