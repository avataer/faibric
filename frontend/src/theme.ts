import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563eb',
      light: '#3b82f6',
      dark: '#1d4ed8',
    },
    secondary: {
      main: '#64748b',
      light: '#94a3b8',
      dark: '#475569',
    },
    background: {
      default: '#ffffff',
      paper: '#ffffff',
    },
    text: {
      primary: '#000000',
      secondary: '#374151',
    },
    success: {
      main: '#16a34a',
    },
    error: {
      main: '#dc2626',
    },
    warning: {
      main: '#d97706',
    },
    info: {
      main: '#2563eb',
    },
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
    allVariants: {
      color: '#000000',
    },
    h1: {
      fontSize: '3rem',
      fontWeight: 700,
      color: '#000000',
    },
    h2: {
      fontSize: '2.5rem',
      fontWeight: 700,
      color: '#000000',
    },
    h3: {
      fontSize: '2rem',
      fontWeight: 600,
      color: '#000000',
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
      color: '#000000',
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 600,
      color: '#000000',
    },
    h6: {
      fontSize: '1.125rem',
      fontWeight: 600,
      color: '#000000',
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.75,
      color: '#000000',
    },
    body2: {
      fontSize: '0.875rem',
      color: '#374151',
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#ffffff',
          color: '#000000',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          padding: '10px 24px',
          borderRadius: '8px',
          boxShadow: 'none',
        },
        contained: {
          backgroundColor: '#2563eb',
          color: '#ffffff',
          '&:hover': {
            backgroundColor: '#1d4ed8',
            boxShadow: '0 2px 8px rgba(37, 99, 235, 0.3)',
          },
        },
        outlined: {
          borderColor: '#2563eb',
          color: '#2563eb',
          borderWidth: '1px',
          '&:hover': {
            borderWidth: '1px',
            backgroundColor: 'rgba(37, 99, 235, 0.05)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#ffffff',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          borderRadius: '8px',
          border: '1px solid #e5e7eb',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: '#ffffff',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#ffffff',
          color: '#000000',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#ffffff',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: '#ffffff',
            '& fieldset': {
              borderColor: '#d1d5db',
            },
            '&:hover fieldset': {
              borderColor: '#9ca3af',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#2563eb',
            },
          },
          '& .MuiInputBase-input': {
            color: '#000000',
          },
          '& .MuiInputLabel-root': {
            color: '#374151',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          color: '#000000',
        },
        head: {
          fontWeight: 600,
          color: '#000000',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: '6px',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
        },
      },
    },
  },
})
