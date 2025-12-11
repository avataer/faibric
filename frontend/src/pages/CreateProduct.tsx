import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, TextField, IconButton, Typography, Container, CircularProgress } from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import { projectsService } from '../services/projects'

const examplePrompts = [
  "A portfolio website for a photographer with gallery sections",
  "A calculator app for converting between currencies",
  "A dashboard showing sales metrics with charts",
  "A contact form with email validation",
  "A todo list app with categories",
  "A landing page for a SaaS product",
]

const CreateProduct = () => {
  const [prompt, setPrompt] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || isLoading) return

    setIsLoading(true)
    try {
      const timestamp = Date.now()
      const randomSuffix = Math.random().toString(36).substring(2, 6)
      const projectName = `Project-${timestamp}-${randomSuffix}`
      
      const response = await projectsService.createProject({
        name: projectName,
        description: prompt.substring(0, 200),
        user_prompt: prompt
      })

      if (response && response.id && !isNaN(response.id)) {
        navigate(`/create/${response.id}`)
      } else {
        console.error('Invalid response:', response)
        alert('Failed to create project')
        setIsLoading(false)
      }
    } catch (error: any) {
      console.error('Failed:', error)
      alert(`Error: ${error?.response?.data?.detail || error?.message || 'Failed to create project'}`)
      setIsLoading(false)
    }
  }

  const handleExampleClick = (example: string) => {
    setPrompt(example)
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Animated background elements */}
      <Box sx={{
        position: 'absolute',
        inset: 0,
        opacity: 0.1,
        background: 'radial-gradient(circle at 20% 50%, #667eea 0%, transparent 50%), radial-gradient(circle at 80% 50%, #764ba2 0%, transparent 50%)',
        animation: 'pulse 8s ease-in-out infinite',
        '@keyframes pulse': {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.1)' }
        }
      }} />

      <Container maxWidth="md" sx={{ position: 'relative', zIndex: 1 }}>
        {/* Logo */}
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, mb: 3 }}>
            <AutoAwesomeIcon sx={{ fontSize: 48, color: '#667eea' }} />
            <Typography variant="h2" sx={{ 
              color: 'white', 
              fontWeight: 800, 
              fontSize: { xs: '2.5rem', md: '4rem' },
              background: 'linear-gradient(90deg, #fff, #667eea)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              Faibric
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ 
            color: 'rgba(255,255,255,0.8)', 
            fontWeight: 400,
            mb: 1
          }}>
            Build Anything with AI
          </Typography>
          <Typography variant="body1" sx={{ 
            color: 'rgba(255,255,255,0.5)', 
          }}>
            Describe what you want, watch it come to life in real-time
          </Typography>
        </Box>

        {/* Main Input */}
        <Box 
          component="form" 
          onSubmit={handleSubmit} 
          sx={{ 
            display: 'flex', 
            gap: 2, 
            background: 'rgba(255,255,255,0.95)', 
            borderRadius: 4, 
            p: 2, 
            boxShadow: '0 25px 80px rgba(102, 126, 234, 0.4)',
            transition: 'all 0.3s ease',
            '&:focus-within': {
              boxShadow: '0 30px 100px rgba(102, 126, 234, 0.5)',
              transform: 'translateY(-2px)'
            }
          }}
        >
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Describe what you want to build..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isLoading}
            variant="standard"
            InputProps={{ 
              disableUnderline: true, 
              sx: { 
                fontSize: '1.2rem', 
                px: 2,
                py: 1,
                fontFamily: 'Inter, system-ui, sans-serif'
              } 
            }}
          />
          <IconButton 
            type="submit" 
            disabled={!prompt.trim() || isLoading} 
            sx={{ 
              bgcolor: '#667eea', 
              color: 'white', 
              width: 56,
              height: 56,
              '&:hover': { bgcolor: '#5a67d8', transform: 'scale(1.05)' }, 
              '&:disabled': { bgcolor: '#e0e0e0' },
              transition: 'all 0.2s ease'
            }}
          >
            {isLoading ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
          </IconButton>
        </Box>

        {/* Example prompts */}
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.4)', mb: 2, display: 'block' }}>
            Try these examples:
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
            {examplePrompts.map((example, i) => (
              <Box
                key={i}
                onClick={() => handleExampleClick(example)}
                sx={{
                  px: 2,
                  py: 1,
                  borderRadius: 3,
                  bgcolor: 'rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.7)',
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    bgcolor: 'rgba(255,255,255,0.2)',
                    color: 'white',
                  }
                }}
              >
                {example.length > 40 ? example.substring(0, 40) + '...' : example}
              </Box>
            ))}
          </Box>
        </Box>

        {/* Footer */}
        <Box sx={{ mt: 6, textAlign: 'center' }}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.3)' }}>
            Powered by OpenAI GPT-4o • V2 Architecture
          </Typography>
        </Box>
      </Container>
    </Box>
  )
}

export default CreateProduct
