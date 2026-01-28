import { useState, useCallback, useRef, useEffect } from 'react'
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  CircularProgress,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import BuildIcon from '@mui/icons-material/Build'
import ChatIcon from '@mui/icons-material/Chat'
import { api } from '../../services/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface PlanningModeProps {
  onReadyToBuild?: (sessionToken: string) => void
  initialRequest?: string
}

type Mode = 'discuss' | 'build'

const PlanningMode = ({ onReadyToBuild, initialRequest }: PlanningModeProps) => {
  const [mode, setMode] = useState<Mode>('discuss')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState(initialRequest || '')
  const [sessionToken, setSessionToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isConverting, setIsConverting] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleModeChange = useCallback(
    (_event: React.MouseEvent<HTMLElement>, newMode: Mode | null) => {
      if (newMode !== null) {
        setMode(newMode)
      }
    },
    []
  )

  const addMessage = useCallback((role: 'user' | 'assistant', content: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${Math.random()}`,
        role,
        content,
        timestamp: new Date(),
      },
    ])
  }, [])

  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    addMessage('user', userMessage)
    setIsLoading(true)

    try {
      const payload: { message?: string; request?: string; session_token?: string } = {}

      if (sessionToken) {
        payload.session_token = sessionToken
        payload.message = userMessage
      } else {
        payload.request = userMessage
      }

      const response = await api.post('/api/onboarding/plan/', payload)

      if (response.data.success) {
        if (!sessionToken && response.data.session_token) {
          setSessionToken(response.data.session_token)
        }
        addMessage('assistant', response.data.response)
      } else {
        addMessage('assistant', response.data.error || 'Something went wrong. Please try again.')
      }
    } catch (error) {
      addMessage('assistant', 'Failed to send message. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, sessionToken, addMessage])

  const handleReadyToBuild = useCallback(async () => {
    if (!sessionToken || isConverting) return

    setIsConverting(true)

    try {
      const response = await api.post('/api/onboarding/plan-to-build/', {
        session_token: sessionToken,
      })

      if (response.data.success) {
        onReadyToBuild?.(sessionToken)
      } else {
        addMessage('assistant', response.data.error || 'Failed to start build. Please try again.')
      }
    } catch (error) {
      addMessage('assistant', 'Failed to start build. Please try again.')
    } finally {
      setIsConverting(false)
    }
  }, [sessionToken, isConverting, onReadyToBuild, addMessage])

  const handleKeyPress = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        handleSend()
      }
    },
    [handleSend]
  )

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        maxWidth: 800,
        mx: 'auto',
        p: 2,
      }}
    >
      {/* Mode Toggle */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
        <ToggleButtonGroup
          value={mode}
          exclusive
          onChange={handleModeChange}
          aria-label="mode selection"
          size="small"
        >
          <ToggleButton value="discuss" aria-label="discuss first">
            <ChatIcon sx={{ mr: 1 }} />
            Discuss First
          </ToggleButton>
          <ToggleButton value="build" aria-label="build now">
            <BuildIcon sx={{ mr: 1 }} />
            Build Now
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {mode === 'discuss' ? (
        <>
          {/* Chat Messages */}
          <Paper
            sx={{
              flex: 1,
              overflow: 'auto',
              p: 2,
              mb: 2,
              backgroundColor: '#f5f5f5',
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}
            elevation={0}
          >
            {messages.length === 0 ? (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: 'text.secondary',
                }}
              >
                <Typography variant="body1">
                  Describe what you want to build and I will help clarify the requirements.
                </Typography>
              </Box>
            ) : (
              messages.map((msg) => (
                <Box
                  key={msg.id}
                  sx={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <Paper
                    sx={{
                      p: 2,
                      maxWidth: '80%',
                      backgroundColor: msg.role === 'user' ? '#1976d2' : '#ffffff',
                      color: msg.role === 'user' ? '#ffffff' : '#000000',
                    }}
                    elevation={1}
                  >
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                      {msg.content}
                    </Typography>
                  </Paper>
                </Box>
              ))
            )}
            {isLoading && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-start' }}>
                <Paper sx={{ p: 2, backgroundColor: '#ffffff' }} elevation={1}>
                  <CircularProgress size={20} />
                </Paper>
              </Box>
            )}
            <div ref={messagesEndRef} />
          </Paper>

          {/* Input Area */}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              placeholder="Describe what you want to build..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              size="small"
            />
            <Button
              variant="contained"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              sx={{ minWidth: 100 }}
            >
              <SendIcon />
            </Button>
          </Box>

          {/* Ready to Build Button */}
          {sessionToken && messages.length > 0 && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
              <Button
                variant="contained"
                color="success"
                size="large"
                onClick={handleReadyToBuild}
                disabled={isConverting}
                startIcon={isConverting ? <CircularProgress size={20} color="inherit" /> : <BuildIcon />}
              >
                {isConverting ? 'Starting Build...' : 'Ready to Build'}
              </Button>
            </Box>
          )}
        </>
      ) : (
        /* Build Now Mode - Direct to build */
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 2,
          }}
        >
          <Typography variant="h6" color="text.secondary">
            Skip planning and build immediately
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            placeholder="Describe what you want to build..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            size="small"
          />
          <Button
            variant="contained"
            color="primary"
            size="large"
            onClick={() => {
              if (input.trim() && onReadyToBuild) {
                onReadyToBuild(input.trim())
              }
            }}
            disabled={!input.trim()}
            startIcon={<BuildIcon />}
          >
            Build Now
          </Button>
        </Box>
      )}
    </Box>
  )
}

export default PlanningMode
