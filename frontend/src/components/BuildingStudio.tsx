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
  const [targetProgress, setTargetProgress] = useState(0) // Smooth animation target
  const lastProgressUpdate = useRef<number>(Date.now())
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
    
    // Start with slow initial progress
    setTargetProgress(3)
    setBuildProgress(0)
    lastProgressUpdate.current = Date.now()
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

        // Use backend progress if provided, otherwise keep current
        if (data.build_progress && data.build_progress > 0) {
          setTargetProgress(data.build_progress)
        }
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
            
            // Calculate progress based on events - NEVER jump more than 15% at a time
            setTargetProgress(prev => {
              let newTarget = prev
              
              if (data.status === 'deployed') {
                newTarget = 100
              } else if (latestMsg.includes('VERIFIED') || latestMsg.includes('live')) {
                newTarget = Math.max(prev, 95)
              } else if (latestMsg.includes('Deploying') || latestMsg.includes('deploying')) {
                newTarget = Math.max(prev, 85)
              } else if (latestMsg.includes('Assembling') || latestMsg.includes('Finalizing')) {
                newTarget = Math.max(prev, 75)
              } else if (latestMsg.includes('footer') || latestMsg.includes('modal')) {
                newTarget = Math.max(prev, 65)
              } else if (latestMsg.includes('form') || latestMsg.includes('feature')) {
                newTarget = Math.max(prev, 55)
              } else if (latestMsg.includes('chart') || latestMsg.includes('stats')) {
                newTarget = Math.max(prev, 45)
              } else if (latestMsg.includes('table') || latestMsg.includes('list')) {
                newTarget = Math.max(prev, 35)
              } else if (latestMsg.includes('navigation') || latestMsg.includes('header')) {
                newTarget = Math.max(prev, 25)
              } else if (latestMsg.includes('layout')) {
                newTarget = Math.max(prev, 18)
              } else if (latestMsg.includes('Building')) {
                newTarget = Math.max(prev, 12)
              } else if (latestMsg.includes('Planning')) {
                newTarget = Math.max(prev, 8)
              } else if (latestMsg.includes('Analyzing')) {
                newTarget = Math.max(prev, 5)
              } else {
                // Small gradual increase
                newTarget = Math.min(70, prev + 3)
              }
              
              // LIMIT: Never jump more than 15% at once (except for 100%)
              if (newTarget < 100) {
                return Math.min(newTarget, prev + 15)
              }
              return newTarget
            })
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

  // Smooth progress animation - VERY gradually approach target
  // This creates realistic, slow progress that never jumps
  useEffect(() => {
    const animateProgress = () => {
      const now = Date.now()
      const timeSinceLastUpdate = now - lastProgressUpdate.current
      
      // Only update every 200ms for smoother animation
      if (timeSinceLastUpdate < 200) return
      
      setBuildProgress(prev => {
        if (prev >= targetProgress) return prev
        
        // SLOW increment: max 2% per update, slower as we get closer to target
        const diff = targetProgress - prev
        const increment = Math.min(2, Math.max(0.5, diff * 0.1))
        const newProgress = Math.min(targetProgress, prev + increment)
        
        lastProgressUpdate.current = now
        return Math.round(newProgress * 10) / 10 // Round to 1 decimal
      })
    }
    
    // Animate continuously while building
    if (isBuilding && buildProgress < targetProgress) {
      const timer = setInterval(animateProgress, 200)
      return () => clearInterval(timer)
    }
  }, [buildProgress, targetProgress, isBuilding])

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
      setBuildProgress(0)
      setTargetProgress(mode === 'modify' ? 50 : 5)  // Modifications start at 50%, new builds at 5%
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
      // Even if API fails, allow user to escape by calling onNewProject
      setIsBuilding(false)
      setMessages(prev => [...prev, {
        id: `stop-error-${Date.now()}`,
        role: 'system',
        content: 'Could not stop build on server. Click "Start New" to begin fresh.',
        timestamp: new Date(),
      }])
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
              <Chip 
                label="Deployed"
                color="success"
                size="small"
              />
            )}
            {/* Always show Start New button */}
            {onNewProject && (
              <Button
                variant="outlined"
                size="small"
                onClick={onNewProject}
                sx={{ ml: 1 }}
              >
                Start New
              </Button>
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
          {/* Priority 1: During build, show live code preview when we have code */}
          {isBuilding && sandpackCode ? (
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
          ) : deploymentUrl && !showLivePreview ? (
            /* Priority 2: Show deployed site when available */
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
          ) : sandpackCode ? (
            /* Priority 3: Show Sandpack if user wants code preview */
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
            /* Priority 4: Show animated progressive preview when no code yet */
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
