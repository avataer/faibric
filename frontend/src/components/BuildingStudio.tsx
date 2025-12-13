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
import StopIcon from '@mui/icons-material/Stop'
import { SandpackProvider, SandpackPreview } from '@codesandbox/sandpack-react'
import { api } from '../services/api'
import ProgressivePreview from './ProgressivePreview'

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
  onNewProject?: () => void
}

const BuildingStudio = ({ sessionToken, initialRequest, onDeployed, onNewProject }: BuildingStudioProps) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isBuilding, setIsBuilding] = useState(true)
  const [buildStatus, setBuildStatus] = useState<string>('initializing')
  const [buildProgress, setBuildProgress] = useState(0)
  const [buildPhase, setBuildPhase] = useState<string>('Starting...')
  const [deploymentUrl, setDeploymentUrl] = useState<string | null>(null)
  const [generatedCode, setGeneratedCode] = useState<string | null>(null)
  const [previewKey, setPreviewKey] = useState(0)
  const [isStopping, setIsStopping] = useState(false)
  const [showLivePreview, setShowLivePreview] = useState(false) // Default to deployed site when ready
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
        content: "I'm building your app now. Watch it come to life in the preview on the right!",
        timestamp: new Date(),
      },
    ])
  }, [initialRequest])

  // Poll for build status - only while building
  useEffect(() => {
    if (!sessionToken) return
    
    // Don't poll if we're deployed and not rebuilding
    if (!isBuilding && deploymentUrl) return

    const pollStatus = async () => {
      try {
        const res = await api.get(`/api/onboarding/status/${sessionToken}/`)
        const data = res.data

        setBuildProgress(data.build_progress || 0)
        setBuildStatus(data.status)

        // Update generated code for live preview
        if (data.generated_code && data.generated_code !== generatedCode) {
          setGeneratedCode(data.generated_code)
          setPreviewKey(prev => prev + 1)
        }

        if (data.deployment_url && data.deployment_url !== deploymentUrl) {
          setDeploymentUrl(data.deployment_url)
          setIsBuilding(false)
          
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
          const progressEvents = data.events
            .filter((e: any) => e.event_type === 'build_progress' && e.event_data?.message)
            .reverse()
          
          if (progressEvents.length > 0) {
            const latestMsg = progressEvents[progressEvents.length - 1].event_data.message
            setBuildPhase(latestMsg)
            
            // Calculate progress based on events
            if (data.status === 'deployed') {
              setBuildProgress(100)
            } else if (latestMsg.includes('Deploying')) {
              setBuildProgress(85)
            } else if (latestMsg.includes('Code generation complete')) {
              setBuildProgress(75)
            } else if (latestMsg.includes('Generated')) {
              setBuildProgress(70)
            } else {
              setBuildProgress(Math.min(60, 10 + progressEvents.length * 5))
            }
          }
          
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
              const errorMsg = `Error: ${latestError.event_data?.error || 'An error occurred'}`
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

    pollStatus()
    const interval = setInterval(pollStatus, 2000)
    return () => clearInterval(interval)
  }, [sessionToken, deploymentUrl, onDeployed, isBuilding]) // Stop polling when deployed

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
    const newRequest = input
    setInput('')

    try {
      // Call the modify endpoint
      const res = await api.post('/api/onboarding/modify/', {
        session_token: sessionToken,
        request: newRequest,
      })
      
      const mode = res.data.mode
      
      // Add assistant acknowledgment based on mode
      setMessages(prev => [...prev, {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: mode === 'modify' 
          ? "Got it! Applying your changes quickly..." 
          : "Starting fresh with your new request...",
        timestamp: new Date(),
      }])
      
      // Reset state for build
      setIsBuilding(true)
      setBuildProgress(mode === 'modify' ? 50 : 0)  // Modifications start at 50%
      setBuildPhase(mode === 'modify' ? 'Modifying code...' : 'Starting new build...')
      setDeploymentUrl(null)
      setGeneratedCode(null)
      setShowLivePreview(false)
      
    } catch (err) {
      console.error('Failed to modify build:', err)
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: 'system',
        content: 'Failed to apply changes. Please try again.',
        timestamp: new Date(),
      }])
    }
  }

  const refreshPreview = () => {
    setPreviewKey(prev => prev + 1)
  }

  const handleStop = async () => {
    setIsStopping(true)
    try {
      await api.post(`/api/onboarding/stop/`, { session_token: sessionToken })
      setIsBuilding(false)
      setMessages(prev => [...prev, {
        id: `stop-${Date.now()}`,
        role: 'system',
        content: 'Build stopped. You can start a new build or make changes.',
        timestamp: new Date(),
      }])
    } catch (err) {
      console.error('Failed to stop build:', err)
    }
    setIsStopping(false)
  }

  // Clean up generated code for Sandpack
  const getSandpackCode = () => {
    if (!generatedCode) return null
    
    let code = generatedCode
    
    // Remove escaped characters
    code = code.replace(/\\n/g, '\n')
    code = code.replace(/\\t/g, '\t')
    code = code.replace(/\\"/g, '"')
    code = code.replace(/\\'/g, "'")
    
    return code
  }

  const sandpackCode = getSandpackCode()

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
              <>
                <Chip 
                  label={`Building... ${buildProgress}%`}
                  color="primary"
                  size="small"
                  icon={<CircularProgress size={14} color="inherit" />}
                />
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  startIcon={<StopIcon />}
                  onClick={handleStop}
                  disabled={isStopping}
                  sx={{ ml: 1 }}
                >
                  {isStopping ? 'Stopping...' : 'Stop'}
                </Button>
              </>
            ) : (
              <>
                <Chip 
                  label="Deployed"
                  color="success"
                  size="small"
                />
                {onNewProject && (
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={onNewProject}
                    sx={{ ml: 1 }}
                  >
                    Start New Project
                  </Button>
                )}
              </>
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
            placeholder={isBuilding ? "Building in progress..." : "Describe changes or request a new website..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !isBuilding && handleSend()}
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="subtitle1" fontWeight={500}>
              Live Preview
            </Typography>
            {deploymentUrl && (
              <Chip
                label={showLivePreview ? "View deployed site" : "View code preview"}
                size="small"
                variant="outlined"
                onClick={() => setShowLivePreview(!showLivePreview)}
                sx={{ cursor: 'pointer' }}
              />
            )}
          </Box>
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
        <Box sx={{ flex: 1, position: 'relative', overflow: 'hidden', backgroundColor: '#fff' }}>
          {/* Priority 1: Show deployed site when available */}
          {deploymentUrl && !showLivePreview ? (
            <iframe
              key={`iframe-${deploymentUrl}`}
              src={deploymentUrl}
              style={{
                width: '100%',
                height: '100%',
                border: 'none',
                backgroundColor: '#fff',
              }}
              title="Your Deployed Website"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            />
          ) : sandpackCode && showLivePreview ? (
            /* Priority 2: Show Sandpack live preview during build */
            <Box sx={{ height: '100%', width: '100%', overflow: 'hidden' }}>
              <SandpackProvider
                key={previewKey}
                template="react-ts"
                theme="light"
                files={{
                  '/App.tsx': {
                    code: sandpackCode,
                    active: true,
                  },
                  '/styles.css': {
                    code: `* { font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif; box-sizing: border-box; } body { margin: 0; padding: 0; }`,
                  },
                }}
                customSetup={{
                  dependencies: {
                    "lucide-react": "latest",
                  },
                }}
              >
                <SandpackPreview 
                  style={{ height: '100%', width: '100%' }}
                  showNavigator={false}
                  showRefreshButton={false}
                />
              </SandpackProvider>
            </Box>
          ) : (
            /* Priority 3: Show animated progressive preview during build */
            <ProgressivePreview 
              progress={buildProgress}
              phase={buildPhase}
              projectName={initialRequest.slice(0, 30)}
              userRequest={initialRequest}
            />
          )}
        </Box>
      </Box>
    </Box>
  )
}

export default BuildingStudio
