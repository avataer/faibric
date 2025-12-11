import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  IconButton,
  CircularProgress,
  Chip,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import RefreshIcon from '@mui/icons-material/Refresh'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { api } from '../services/api'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

interface BuildingStudioProps {
  sessionToken: string
  initialRequest: string
  onDeployed?: (url: string) => void
}

const BuildingStudio = ({ sessionToken, initialRequest, onDeployed }: BuildingStudioProps) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isBuilding, setIsBuilding] = useState(true)
  const [buildStatus, setBuildStatus] = useState<string>('initializing')
  const [buildProgress, setBuildProgress] = useState(0)
  const [deploymentUrl, setDeploymentUrl] = useState<string | null>(null)
  const [previewKey, setPreviewKey] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialize with the user's request
  useEffect(() => {
    setMessages([
      {
        id: '1',
        role: 'user',
        content: initialRequest,
        timestamp: new Date(),
      },
      {
        id: '2',
        role: 'assistant',
        content: "I'm building your app now. You can see it taking shape in the preview on the right. Feel free to ask for changes or additions while I work!",
        timestamp: new Date(),
      },
    ])
  }, [initialRequest])

  // Poll for build status
  useEffect(() => {
    if (!sessionToken) return

    const pollStatus = async () => {
      try {
        const res = await api.get(`/api/onboarding/status/${sessionToken}/`)
        const data = res.data

        setBuildProgress(data.build_progress || 0)
        setBuildStatus(data.status)

        if (data.deployment_url && data.deployment_url !== deploymentUrl) {
          setDeploymentUrl(data.deployment_url)
          setIsBuilding(false)
          setPreviewKey(prev => prev + 1)
          
          // Add system message about deployment
          setMessages(prev => [...prev, {
            id: `deploy-${Date.now()}`,
            role: 'system',
            content: `Your app is live at ${data.deployment_url}`,
            timestamp: new Date(),
          }])

          if (onDeployed) {
            onDeployed(data.deployment_url)
          }
        }

        // Add ALL build_progress events as system messages
        if (data.events && data.events.length > 0) {
          // Process events in reverse order (oldest first) to maintain chronological order
          const progressEvents = data.events
            .filter((e: any) => e.event_type === 'build_progress' && e.event_data?.message)
            .reverse()
          
          setMessages(prev => {
            let updated = [...prev]
            for (const event of progressEvents) {
              const msg = event.event_data.message
              const eventId = event.id || `event-${event.timestamp}`
              const exists = updated.some(m => m.id === eventId || m.content === msg)
              if (!exists) {
                updated.push({
                  id: eventId,
                  role: 'system',
                  content: msg,
                  timestamp: new Date(event.timestamp),
                })
              }
            }
            return updated
          })
        }
        
        // Also add error events
        if (data.events) {
          const errorEvents = data.events.filter((e: any) => e.event_type === 'error')
          if (errorEvents.length > 0) {
            const latestError = errorEvents[0]
            setMessages(prev => {
              const errorMsg = `⚠️ ${latestError.event_data?.error || 'An error occurred'}`
              const exists = prev.some(m => m.content === errorMsg)
              if (!exists) {
                return [...prev, {
                  id: `error-${Date.now()}`,
                  role: 'system',
                  content: errorMsg,
                  timestamp: new Date(),
                }]
              }
              return prev
            })
          }
        }
      } catch (err) {
        console.error('Status poll failed:', err)
      }
    }

    // Poll immediately and then every 2 seconds for faster updates
    pollStatus()
    const interval = setInterval(pollStatus, 2000)
    return () => clearInterval(interval)
  }, [sessionToken, deploymentUrl, onDeployed])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')

    // TODO: Send to backend for iterative changes
    // For now, just acknowledge
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: "I'll incorporate that change. The preview will update shortly.",
        timestamp: new Date(),
      }])
    }, 1000)
  }

  const refreshPreview = () => {
    setPreviewKey(prev => prev + 1)
  }

  return (
    <Box sx={{ 
      display: 'flex', 
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
    }}>
      {/* Left Panel - Chat */}
      <Box sx={{ 
        width: '40%', 
        minWidth: 400,
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid #e5e7eb',
        backgroundColor: '#ffffff',
      }}>
        {/* Header */}
        <Box sx={{ 
          p: 2, 
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <Typography variant="h6" fontWeight={600}>
            Faibric Studio
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            {isBuilding ? (
              <Chip 
                label={`Building... ${buildProgress}%`}
                color="primary"
                size="small"
                icon={<CircularProgress size={14} color="inherit" />}
              />
            ) : (
              <Chip 
                label="Deployed"
                color="success"
                size="small"
              />
            )}
          </Box>
        </Box>

        {/* Messages */}
        <Box sx={{ 
          flex: 1, 
          overflow: 'auto',
          p: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
        }}>
          {messages.map((msg) => (
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
                  backgroundColor: 
                    msg.role === 'user' ? '#3b82f6' : 
                    msg.role === 'system' ? '#f3f4f6' : '#ffffff',
                  color: msg.role === 'user' ? '#ffffff' : '#000000',
                  border: msg.role === 'assistant' ? '1px solid #e5e7eb' : 'none',
                }}
                elevation={msg.role === 'system' ? 0 : 1}
              >
                {msg.role === 'system' ? (
                  <Typography variant="body2" sx={{ fontStyle: 'italic', color: '#6b7280' }}>
                    {msg.content}
                  </Typography>
                ) : (
                  <Typography variant="body1">{msg.content}</Typography>
                )}
              </Paper>
            </Box>
          ))}
          <div ref={messagesEndRef} />
        </Box>

        {/* Input */}
        <Box sx={{ 
          p: 2, 
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          gap: 1,
        }}>
          <TextField
            fullWidth
            placeholder="Ask for changes or additions..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            size="small"
            disabled={isBuilding}
          />
          <IconButton 
            color="primary" 
            onClick={handleSend}
            disabled={!input.trim() || isBuilding}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Right Panel - Preview */}
      <Box sx={{ 
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#f9fafb',
      }}>
        {/* Preview Header */}
        <Box sx={{ 
          p: 2, 
          borderBottom: '1px solid #e5e7eb',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#ffffff',
        }}>
          <Typography variant="subtitle1" fontWeight={500}>
            Live Preview
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton size="small" onClick={refreshPreview} title="Refresh preview">
              <RefreshIcon />
            </IconButton>
            {deploymentUrl && (
              <IconButton 
                size="small" 
                onClick={() => window.open(deploymentUrl, '_blank')}
                title="Open in new tab"
              >
                <OpenInNewIcon />
              </IconButton>
            )}
          </Box>
        </Box>

        {/* Preview Content */}
        <Box sx={{ flex: 1, position: 'relative' }}>
          {deploymentUrl ? (
            <iframe
              key={previewKey}
              src={deploymentUrl}
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
              }}
              title="App Preview"
            />
          ) : (
            <Box sx={{ 
              display: 'flex', 
              flexDirection: 'column',
              alignItems: 'center', 
              justifyContent: 'center',
              height: '100%',
              gap: 2,
            }}>
              <CircularProgress size={48} />
              <Typography variant="h6" color="text.secondary">
                Building your app...
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {buildProgress}% complete
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ maxWidth: 400, textAlign: 'center' }}>
                Your app will appear here once it's deployed. This usually takes 2-5 minutes.
              </Typography>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  )
}

export default BuildingStudio
