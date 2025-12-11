import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Box, Typography, Paper, TextField, IconButton, Button, CircularProgress } from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import RefreshIcon from '@mui/icons-material/Refresh'
import { projectsService } from '../services/projects'

interface AIMessage {
  id: string
  type: 'thinking' | 'action' | 'success' | 'error'
  content: string
  timestamp: number
}

const LiveCreation = () => {
  const { id } = useParams<{ id: string }>()
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [deploymentUrl, setDeploymentUrl] = useState<string>('')
  const [isBuilding, setIsBuilding] = useState(true)
  const [userMessage, setUserMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string>('')
  const [isReloading, setIsReloading] = useState(false)
  const [projectStatus, setProjectStatus] = useState<string>('')
  const chatEndRef = useRef<HTMLDivElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const pollCountRef = useRef(0)

  // Polling function - separated to avoid dependency issues
  const pollProject = useCallback(async () => {
    if (!id || isNaN(Number(id))) return

    try {
      const [progress, project] = await Promise.all([
        projectsService.getProgress(Number(id)),
        projectsService.getProject(Number(id))
      ])

      // Clear any previous errors
      setError('')
      pollCountRef.current++

      // Update messages from the backend (merge with local messages)
      if (progress.messages && Array.isArray(progress.messages)) {
        const backendMessages = progress.messages.map((msg: any) => ({
          id: msg.id,
          type: msg.type,
          content: msg.content,
          timestamp: new Date(msg.timestamp).getTime()
        }))
        
        // Smart merge: keep local messages, add new backend messages
        setMessages(prev => {
          // Keep all local messages (user_, processing_, error_)
          const localMessages = prev.filter(m => 
            m.id.startsWith('user_') || 
            m.id.startsWith('processing_') || 
            m.id.startsWith('error_')
          )
          
          // If we got new backend messages, remove "processing_" messages (they're done)
          const hasNewBackendMessages = backendMessages.length > prev.filter(m => !m.id.startsWith('user_') && !m.id.startsWith('processing_') && !m.id.startsWith('error_')).length
          const filteredLocalMessages = hasNewBackendMessages 
            ? localMessages.filter(m => !m.id.startsWith('processing_'))
            : localMessages
          
          // Combine: local messages + backend messages (no duplicates)
          const existingIds = new Set(filteredLocalMessages.map(m => m.id))
          const newBackendMessages = backendMessages.filter((m: AIMessage) => !existingIds.has(m.id))
          
          const all = [...filteredLocalMessages, ...newBackendMessages]
          return all.sort((a, b) => a.timestamp - b.timestamp)
        })
      }

      // Always update deployment URL when available
      if (project.deployment_url) {
        setDeploymentUrl(project.deployment_url)
      }

      // Check if status changed from deploying to deployed (trigger refresh)
      const wasDeploying = projectStatus === 'deploying' || projectStatus === 'building'
      const nowDeployed = project.status === 'deployed'
      
      // Update project status
      setProjectStatus(project.status)

      // Update building status based on project status
      if (project.status === 'deployed') {
        setIsBuilding(false)
        // Auto-refresh iframe if just finished deploying
        if (wasDeploying && iframeRef.current && project.deployment_url) {
          console.log('Auto-refreshing iframe after deployment')
          const cacheBuster = `?t=${Date.now()}`
          iframeRef.current.src = project.deployment_url + cacheBuster
        }
      } else if (project.status === 'deploying' || project.status === 'generating' || project.status === 'building') {
        setIsBuilding(true)
      } else if (project.status === 'ready') {
        setIsBuilding(false)
      } else if (project.status === 'failed') {
        setIsBuilding(false)
        setError('Project generation failed. Please try again.')
      }

      console.log(`[Poll ${pollCountRef.current}] Status: ${project.status}, URL: ${project.deployment_url || 'none'}`)

    } catch (error: any) {
      console.error('Failed to get progress:', error)
      // Don't set error immediately - might be transient
      if (pollCountRef.current > 5) {
        setError(error?.response?.data?.detail || 'Failed to load project')
      }
    }
  }, [id])

  // Start polling on mount
  useEffect(() => {
    if (!id || isNaN(Number(id))) {
      setError('Invalid project ID')
      return
    }

    // Initial poll
    pollProject()

    // Set up interval
    const interval = setInterval(pollProject, 1000) // Poll every second

    return () => clearInterval(interval)
  }, [id, pollProject])

  // Auto-scroll chat only when new messages are added (not on every render)
  const prevMessageCount = useRef(0)
  useEffect(() => {
    if (messages.length > prevMessageCount.current) {
      // Only scroll if user is near the bottom already
      const chatContainer = chatEndRef.current?.parentElement
      if (chatContainer) {
        const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 150
        if (isNearBottom) {
          chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
        }
      }
      prevMessageCount.current = messages.length
    }
  }, [messages])

  // Auto-reload iframe when URL changes
  useEffect(() => {
    if (deploymentUrl && iframeRef.current) {
      console.log('Setting iframe src to:', deploymentUrl)
      const cacheBuster = `?t=${Date.now()}`
      iframeRef.current.src = deploymentUrl + cacheBuster
    }
  }, [deploymentUrl])

  const handleSendMessage = async () => {
    if (!userMessage.trim() || isSending || !id) return

    setIsSending(true)
    setIsBuilding(true)
    
    const messageToSend = userMessage
    setUserMessage('')

    // Add user's message to chat immediately
    const userMsg: AIMessage = {
      id: `user_${Date.now()}`,
      type: 'action',
      content: `💬 You: ${messageToSend}`,
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, userMsg])

    try {
      await projectsService.quickUpdate(Number(id), messageToSend)
      // Add "processing" message
      const processingMsg: AIMessage = {
        id: `processing_${Date.now()}`,
        type: 'thinking',
        content: '🔄 Processing your request...',
        timestamp: Date.now()
      }
      setMessages(prev => [...prev, processingMsg])
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMsg: AIMessage = {
        id: `error_${Date.now()}`,
        type: 'error',
        content: '❌ Failed to apply update. Please try again.',
        timestamp: Date.now()
      }
      setMessages(prev => [...prev, errorMsg])
      setIsBuilding(false)
    } finally {
      setIsSending(false)
    }
  }

  const handleRefresh = () => {
    if (iframeRef.current && deploymentUrl) {
      setIsReloading(true)
      const cacheBuster = `?t=${Date.now()}`
      iframeRef.current.src = deploymentUrl + cacheBuster
      setTimeout(() => setIsReloading(false), 2000)
    }
  }

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {error ? (
        <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#1a1a2e' }}>
          <Box sx={{ textAlign: 'center', color: 'white', p: 4 }}>
            <Typography variant="h5" sx={{ mb: 2, color: '#ef4444' }}>⚠️ Error</Typography>
            <Typography variant="body1" sx={{ mb: 3 }}>{error}</Typography>
            <Button variant="outlined" onClick={() => window.location.href = '/dashboard'} sx={{ color: 'white', borderColor: 'white' }}>
              Go to Dashboard
            </Button>
          </Box>
        </Box>
      ) : (
        <>
          {/* Left side - Preview */}
          <Box sx={{ flex: 1, bgcolor: '#1a1a2e', display: 'flex', flexDirection: 'column', position: 'relative' }}>
            {deploymentUrl ? (
              <>
                {/* URL bar */}
                <Box sx={{ bgcolor: '#0a0e1a', py: 1.5, px: 3, borderBottom: '1px solid #2d3748', display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Box sx={{ bgcolor: '#1a1f2e', color: '#9ca3af', px: 3, py: 1, borderRadius: 2, fontSize: '0.9rem', flex: 1, fontFamily: 'monospace' }}>
                    {deploymentUrl}
                  </Box>
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={isReloading ? <CircularProgress size={16} /> : <RefreshIcon />}
                    disabled={isReloading}
                    onClick={handleRefresh}
                    sx={{ color: 'white', borderColor: '#4b5563', '&:hover': { borderColor: '#667eea', bgcolor: 'rgba(102, 126, 234, 0.1)' } }}
                  >
                    {isReloading ? 'Loading...' : 'Refresh'}
                  </Button>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={() => window.open(deploymentUrl, '_blank')}
                    sx={{ bgcolor: '#667eea', '&:hover': { bgcolor: '#5a67d8' } }}
                  >
                    Open
                  </Button>
                </Box>
                {/* iframe */}
                <Box sx={{ flex: 1, position: 'relative' }}>
                  <iframe 
                    ref={iframeRef} 
                    style={{ width: '100%', height: '100%', border: 'none', background: 'white' }} 
                    title="Live Product" 
                  />
                  {isBuilding && (
                    <Box sx={{ 
                      position: 'absolute', 
                      inset: 0, 
                      bgcolor: 'rgba(0,0,0,0.7)', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      color: 'white'
                    }}>
                      <Box sx={{ textAlign: 'center' }}>
                        <CircularProgress sx={{ color: '#667eea', mb: 2 }} />
                        <Typography>Updating...</Typography>
                      </Box>
                    </Box>
                  )}
                </Box>
              </>
            ) : (
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'white', position: 'relative' }}>
                <Box sx={{ textAlign: 'center', zIndex: 10 }}>
                  <Typography variant="h4" sx={{ mb: 2, fontWeight: 600 }}>
                    ⚡ Building Your App
                  </Typography>
                  <Typography variant="body1" sx={{ opacity: 0.7, mb: 3, maxWidth: 400 }}>
                    {messages.length > 0 ? messages[messages.length - 1].content : 'Initializing AI...'}
                  </Typography>
                  <CircularProgress sx={{ color: '#667eea' }} size={48} />
                  <Typography variant="caption" sx={{ display: 'block', mt: 2, opacity: 0.5 }}>
                    Status: {projectStatus || 'starting'}
                  </Typography>
                </Box>
                {/* Animated background */}
                <Box sx={{
                  position: 'absolute',
                  inset: 0,
                  opacity: 0.1,
                  background: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(102, 126, 234, 0.3) 10px, rgba(102, 126, 234, 0.3) 20px)',
                  animation: 'slide 20s linear infinite',
                  '@keyframes slide': {
                    '0%': { backgroundPosition: '0 0' },
                    '100%': { backgroundPosition: '1000px 1000px' }
                  }
                }} />
              </Box>
            )}
          </Box>

          {/* Right side - Chat */}
          <Box sx={{ width: 400, bgcolor: '#f8fafc', borderLeft: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 3, borderBottom: '1px solid #e2e8f0', bgcolor: 'white' }}>
              <Typography variant="h6" fontWeight={600}>AI Building Process</Typography>
              <Typography variant="caption" color="text.secondary">Watch as AI creates your product</Typography>
            </Box>

            <Box sx={{ flex: 1, overflowY: 'auto', p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
              {messages.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <CircularProgress size={24} sx={{ mb: 2 }} />
                  <Typography variant="body2" color="text.secondary">Waiting for AI...</Typography>
                </Box>
              )}

              {messages.map((message) => {
                const isUserMessage = message.id.startsWith('user_')
                const isProcessing = message.id.startsWith('processing_')
                
                return (
                  <Paper key={message.id} elevation={0} sx={{ 
                    p: 2, 
                    bgcolor: isUserMessage ? '#eff6ff' : message.type === 'success' ? '#f0fdf4' : message.type === 'error' ? '#fef2f2' : isProcessing ? '#fef9c3' : '#f8fafc', 
                    border: '1px solid', 
                    borderColor: isUserMessage ? '#93c5fd' : message.type === 'success' ? '#86efac' : message.type === 'error' ? '#fecaca' : isProcessing ? '#fde047' : '#e2e8f0', 
                    borderRadius: 2,
                    ml: isUserMessage ? 2 : 0,
                  }}>
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                      <Box sx={{ 
                        width: 8, 
                        height: 8, 
                        borderRadius: '50%', 
                        bgcolor: isUserMessage ? '#3b82f6' : message.type === 'success' ? '#10b981' : message.type === 'error' ? '#ef4444' : isProcessing ? '#eab308' : '#3b82f6', 
                        mt: 0.5, 
                        flexShrink: 0 
                      }} />
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="body2" sx={{ 
                          color: isUserMessage ? '#1e40af' : message.type === 'success' ? '#166534' : message.type === 'error' ? '#991b1b' : '#1e293b', 
                          lineHeight: 1.6,
                          fontWeight: isUserMessage ? 500 : 400
                        }}>
                          {message.content}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#64748b', display: 'block', mt: 0.5 }}>
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </Typography>
                      </Box>
                    </Box>
                  </Paper>
                )
              })}

              <div ref={chatEndRef} />
            </Box>

            <Box sx={{ p: 2, borderTop: '1px solid #e2e8f0', bgcolor: 'white' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                {isBuilding ? (
                  <>
                    <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#3b82f6', animation: 'pulse 2s ease-in-out infinite', '@keyframes pulse': { '0%, 100%': { opacity: 1 }, '50%': { opacity: 0.5 } } }} />
                    <Typography variant="caption" fontWeight={500} color="primary">Building...</Typography>
                  </>
                ) : (
                  <>
                    <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#10b981' }} />
                    <Typography variant="caption" fontWeight={500} sx={{ color: '#10b981' }}>Live</Typography>
                  </>
                )}
              </Box>
              
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Request changes (e.g., 'Make it darker')"
                  value={userMessage}
                  onChange={(e) => setUserMessage(e.target.value)}
                  disabled={isSending}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSendMessage()
                    }
                  }}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
                <IconButton 
                  color="primary" 
                  onClick={handleSendMessage}
                  disabled={!userMessage.trim() || isSending}
                  sx={{ bgcolor: '#667eea', color: 'white', '&:hover': { bgcolor: '#5a67d8' }, '&:disabled': { bgcolor: '#e0e0e0' } }}
                >
                  <SendIcon />
                </IconButton>
              </Box>
            </Box>
          </Box>
        </>
      )}
    </Box>
  )
}

export default LiveCreation
