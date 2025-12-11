import { Drawer, List, ListItem, ListItemButton, ListItemText, Box, Typography } from '@mui/material'
import { Link, useLocation } from 'react-router-dom'

const drawerWidth = 240

const menuItems = [
  { text: 'Dashboard', path: '/dashboard' },
  { text: 'My Projects', path: '/dashboard' },
  { text: 'Account', path: '/account' },
  { text: 'Panel Builder', path: '/panel-builder' },
]

const Sidebar = () => {
  const location = useLocation()

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          bgcolor: '#ffffff',
          borderRight: '1px solid #e5e7eb',
        },
      }}
    >
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ color: '#000000', fontWeight: 700 }}>
          Faibric
        </Typography>
      </Box>
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding>
            <ListItemButton
              component={Link}
              to={item.path}
              selected={location.pathname === item.path}
              sx={{
                '&.Mui-selected': {
                  bgcolor: '#f3f4f6',
                },
                '&:hover': {
                  bgcolor: '#f9fafb',
                },
              }}
            >
              <ListItemText 
                primary={item.text} 
                sx={{ 
                  '& .MuiListItemText-primary': { 
                    color: '#000000',
                    fontWeight: location.pathname === item.path ? 600 : 400,
                  } 
                }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Drawer>
  )
}

export default Sidebar
