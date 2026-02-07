import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Box, Typography, Paper, TextField, IconButton, Button, CircularProgress, LinearProgress, Chip } from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import RefreshIcon from '@mui/icons-material/Refresh'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import LanguageIcon from '@mui/icons-material/Language'
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline'
import { projectsService } from '../services/projects'
import ProgressivePreview from '../components/ProgressivePreview'

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
  const [buildProgress, setBuildProgress] = useState<number>(0)
  const [displayProgress, setBuildProgressSmooth] = useState<number>(0)
  const [currentPhase, setCurrentPhase] = useState<string>('Initializing...')
  const [aiTimedOut, setAiTimedOut] = useState(false)
  
  // Smoothly interpolate progress
  useEffect(() => {
    if (displayProgress < buildProgress) {
      const diff = buildProgress - displayProgress
      const step = Math.max(0.1, diff / 20) // Smooth movement
      const timer = setTimeout(() => {
        setBuildProgressSmooth(prev => Math.min(prev + step, buildProgress))
      }, 50)
      return () => clearTimeout(timer)
    }
  }, [buildProgress, displayProgress])
  const chatEndRef = useRef<HTMLDivElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const pollCountRef = useRef(0)
  const buildStartTimeRef = useRef<number>(Date.now())

  // Track previous status for detecting transitions
  const prevStatusRef = useRef<string>('')

  // AI timeout: if no progress after 10 seconds, show fallback
  // Reduced from 15s to detect AI unavailability faster
  useEffect(() => {
    if (!isBuilding || aiTimedOut) return
    const timer = setTimeout(() => {
      if (isBuilding && messages.length === 0 && buildProgress === 0 && !deploymentUrl) {
        setAiTimedOut(true)
        setIsBuilding(false)
        setCurrentPhase('AI service unavailable - showing project preview')
      }
    }, 10000)
    return () => clearTimeout(timer)
  }, [isBuilding, aiTimedOut, messages.length, buildProgress, deploymentUrl])

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
        // Update build progress if available
        if (progress.progress !== undefined) {
          setBuildProgress(progress.progress)
        }

        const backendMessages = progress.messages.map((msg: any) => ({
          id: msg.id,
          type: msg.type,
          content: msg.content,
          timestamp: new Date(msg.timestamp).getTime()
        }))

        if (backendMessages.length > 0) {
          setCurrentPhase(backendMessages[backendMessages.length - 1].content)
        }

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
      const wasDeploying = prevStatusRef.current === 'deploying' || prevStatusRef.current === 'building'

      // Update project status
      setProjectStatus(project.status)
      prevStatusRef.current = project.status

      // Update building status based on project status
      if (project.status === 'deployed') {
        setIsBuilding(false)
        setAiTimedOut(false)
        // Auto-refresh iframe if just finished deploying
        if (wasDeploying && iframeRef.current && project.deployment_url) {
          const cacheBuster = `?t=${Date.now()}`
          iframeRef.current.src = project.deployment_url + cacheBuster
        }
      } else if (['deploying', 'generating', 'building'].includes(project.status as string)) {
        if (!aiTimedOut) {
          setIsBuilding(true)
        }
      } else if (project.status === 'ready') {
        setIsBuilding(false)
      } else if (project.status === 'failed') {
        setIsBuilding(false)
        setError('Project generation failed. Please try again.')
      }

    } catch (error: any) {
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

    // Set up interval - poll every 2 seconds (less aggressive than 1s)
    const interval = setInterval(pollProject, 2000)

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
    } catch {
      const errorMsg: AIMessage = {
        id: `error_${Date.now()}`,
        type: 'error',
        content: 'Failed to apply update. Please try again.',
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
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden', backgroundColor: '#ffffff' }}>
      {error ? (
        <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: '#ffffff' }}>
          <Paper elevation={0} sx={{
            textAlign: 'center',
            p: 5,
            maxWidth: 440,
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 3,
          }}>
            <ErrorOutlineIcon sx={{ fontSize: 48, color: '#dc2626', mb: 2 }} />
            <Typography variant="h5" sx={{ mb: 1.5, color: '#991b1b', fontWeight: 600 }}>
              Something went wrong
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, color: '#7f1d1d' }}>{error}</Typography>
            <Button
              variant="contained"
              onClick={() => window.location.href = '/dashboard'}
              startIcon={<RefreshIcon />}
              sx={{
                backgroundColor: '#dc2626',
                textTransform: 'none',
                borderRadius: 2,
                '&:hover': { backgroundColor: '#b91c1c' },
              }}
            >
              Go to Dashboard
            </Button>
          </Paper>
        </Box>
      ) : (
        <>
          {/* Left side - Preview (~60%) */}
          <Box sx={{
            flex: 1.5,
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#f9fafb',
            position: 'relative',
          }}>
            {/* Browser Chrome */}
            <Box sx={{
              backgroundColor: '#f8f9fa',
              borderBottom: '1px solid #e0e0e0',
            }}>
              {/* Top bar with traffic lights, URL bar, and actions */}
              <Box sx={{
                px: 2,
                py: 1,
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
              }}>
                {/* Traffic light dots */}
                <Box sx={{ display: 'flex', gap: 0.75, flexShrink: 0 }}>
                  <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ff5f57' }} />
                  <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#febc2e' }} />
                  <Box sx={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#28c840' }} />
                </Box>

                {/* URL bar */}
                <Box sx={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e0e0e0',
                  borderRadius: 2,
                  px: 1.5,
                  py: 0.5,
                  gap: 1,
                  minWidth: 0,
                }}>
                  <LanguageIcon sx={{ fontSize: 14, color: '#9ca3af', flexShrink: 0 }} />
                  <Typography
                    variant="body2"
                    sx={{
                      color: '#6b7280',
                      fontSize: '0.75rem',
                      fontFamily: '"SF Mono", "Fira Code", "Fira Mono", Menlo, monospace',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {deploymentUrl || 'about:blank'}
                  </Typography>
                </Box>

                {/* Action buttons */}
                <Box sx={{ display: 'flex', gap: 0.5, flexShrink: 0 }}>
                  <IconButton
                    size="small"
                    onClick={handleRefresh}
                    disabled={isReloading || !deploymentUrl}
                    sx={{
                      width: 30,
                      height: 30,
                      color: '#6b7280',
                      '&:hover': { backgroundColor: '#e5e7eb', color: '#374151' },
                    }}
                  >
                    {isReloading ? <CircularProgress size={14} /> : <RefreshIcon sx={{ fontSize: 16 }} />}
                  </IconButton>
                  {deploymentUrl && (
                    <IconButton
                      size="small"
                      onClick={() => window.open(deploymentUrl, '_blank')}
                      sx={{
                        width: 30,
                        height: 30,
                        color: '#6b7280',
                        '&:hover': { backgroundColor: '#e5e7eb', color: '#374151' },
                      }}
                    >
                      <OpenInNewIcon sx={{ fontSize: 16 }} />
                    </IconButton>
                  )}
                </Box>
              </Box>
            </Box>

            {/* Preview Content */}
            <Box sx={{
              flex: 1,
              position: 'relative',
              overflow: 'hidden',
              m: 1.5,
              borderRadius: '0 0 10px 10px',
              border: '1px solid #e0e0e0',
              boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
              backgroundColor: '#ffffff',
            }}>
              {deploymentUrl ? (
                <>
                  <iframe
                    ref={iframeRef}
                    style={{ width: '100%', height: '100%', border: 'none', background: 'white' }}
                    title="Live Product"
                  />
                  {isBuilding && (
                    <Box sx={{
                      position: 'absolute',
                      inset: 0,
                      bgcolor: 'rgba(255,255,255,0.85)',
                      backdropFilter: 'blur(4px)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      zIndex: 100,
                    }}>
                      <Box sx={{ textAlign: 'center', maxWidth: 320 }}>
                        <CircularProgress sx={{ color: '#1976d2', mb: 2 }} size={40} />
                        <Typography variant="h6" sx={{ color: '#111827', fontWeight: 600 }}>
                          Updating your app...
                        </Typography>
                        <Typography variant="body2" sx={{ color: '#6b7280', mt: 0.5 }}>
                          {currentPhase}
                        </Typography>
                      </Box>
                    </Box>
                  )}
                </>
              ) : aiTimedOut ? (
                <Box sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  gap: 3,
                  p: 4,
                  backgroundColor: '#fafafa',
                }}>
                  <ErrorOutlineIcon sx={{ fontSize: 56, color: '#94a3b8' }} />
                  <Typography variant="h5" sx={{ fontWeight: 600, color: '#111827' }}>
                    AI Service Unavailable
                  </Typography>
                  <Typography variant="body1" sx={{ color: '#6b7280', textAlign: 'center', maxWidth: 420 }}>
                    The AI building service is not responding. Your project exists but no preview is available yet.
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#9ca3af', textAlign: 'center', maxWidth: 400 }}>
                    You can send chat messages and they will be processed once the AI service comes back online.
                  </Typography>
                  <Button
                    variant="contained"
                    startIcon={<RefreshIcon />}
                    onClick={() => {
                      setAiTimedOut(false)
                      setIsBuilding(true)
                      buildStartTimeRef.current = Date.now()
                      pollCountRef.current = 0
                    }}
                    sx={{
                      backgroundColor: '#1976d2',
                      textTransform: 'none',
                      borderRadius: 2,
                      '&:hover': { backgroundColor: '#1565c0' },
                    }}
                  >
                    Retry Connection
                  </Button>
                </Box>
              ) : (
                <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
                  <Box sx={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
                    <ProgressivePreview
                      progress={displayProgress}
                      phase={currentPhase}
                      projectName={id}
                      userRequest={messages.find(m => m.id.startsWith('user_'))?.content || ''}
                    />

                    {/* Overlay progress info */}
                    <Box sx={{
                      position: 'absolute',
                      top: 24,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      bgcolor: 'rgba(255,255,255,0.95)',
                      backdropFilter: 'blur(10px)',
                      px: 3,
                      py: 1.5,
                      borderRadius: 3,
                      border: '1px solid #e0e0e0',
                      boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
                      zIndex: 10,
                      textAlign: 'center',
                      minWidth: 300,
                    }}>
                      <Typography variant="subtitle2" sx={{ color: '#1976d2', fontWeight: 700, mb: 0.5, fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                        BUILDING YOUR CUSTOM PROJECT
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <LinearProgress
                          variant="determinate"
                          value={displayProgress}
                          sx={{
                            flex: 1,
                            height: 5,
                            borderRadius: 2,
                            backgroundColor: '#e5e7eb',
                            '& .MuiLinearProgress-bar': {
                              borderRadius: 2,
                              backgroundColor: '#1976d2',
                              transition: 'transform 0.1s linear',
                            },
                          }}
                        />
                        <Typography variant="caption" sx={{ fontWeight: 700, color: '#1976d2' }}>
                          {Math.round(displayProgress)}%
                        </Typography>
                      </Box>
                      <Typography variant="caption" sx={{ color: '#6b7280', mt: 0.5, display: 'block' }}>
                        {currentPhase}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              )}
            </Box>
          </Box>

          {/* Right side - Chat (~40%) */}
          <Box sx={{
            width: '40%',
            minWidth: 380,
            borderLeft: '1px solid #e5e7eb',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: '#ffffff',
          }}>
            {/* Chat Header */}
            <Box sx={{
              px: 2.5,
              py: 2,
              borderBottom: '1px solid #e5e7eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: '#ffffff',
            }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AutoAwesomeIcon sx={{ color: '#1976d2', fontSize: 22 }} />
                <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem', color: '#111827' }}>
                  AI Builder
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                {isBuilding ? (
                  <Chip
                    label="Building"
                    size="small"
                    sx={{
                      backgroundColor: '#eff6ff',
                      color: '#1976d2',
                      fontWeight: 600,
                      fontSize: '0.75rem',
                      '@keyframes pulse-dot': {
                        '0%, 100%': { opacity: 1 },
                        '50%': { opacity: 0.4 },
                      },
                      '&::before': {
                        content: '""',
                        display: 'inline-block',
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        backgroundColor: '#1976d2',
                        marginRight: '6px',
                        animation: 'pulse-dot 1.2s ease-in-out infinite',
                      },
                    }}
                  />
                ) : (
                  <Chip
                    label="Ready"
                    size="small"
                    sx={{
                      backgroundColor: '#f0fdf4',
                      color: '#16a34a',
                      fontWeight: 600,
                      fontSize: '0.75rem',
                    }}
                  />
                )}
              </Box>
            </Box>

            {/* Build Progress Bar */}
            {isBuilding && (
              <Box sx={{ px: 2.5, py: 1.5, backgroundColor: '#f8f9fa' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" sx={{ color: '#6b7280', fontWeight: 500 }}>
                    {currentPhase || 'Building your website...'}
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#1976d2', fontWeight: 600 }}>
                    {Math.round(displayProgress)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={displayProgress}
                  sx={{
                    height: 5,
                    borderRadius: 2,
                    backgroundColor: '#e5e7eb',
                    '& .MuiLinearProgress-bar': {
                      borderRadius: 2,
                      backgroundColor: '#1976d2',
                      '@keyframes shimmer': {
                        '0%': { opacity: 1 },
                        '50%': { opacity: 0.7 },
                        '100%': { opacity: 1 },
                      },
                      animation: 'shimmer 1.5s ease-in-out infinite',
                    },
                  }}
                />
              </Box>
            )}

            {/* Messages */}
            <Box sx={{
              flex: 1,
              overflowY: 'auto',
              px: 2,
              py: 2,
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
              backgroundColor: '#f8f9fa',
            }}>
              {messages.length === 0 && !aiTimedOut && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <CircularProgress size={24} sx={{ mb: 2, color: '#1976d2' }} />
                  <Typography variant="body2" color="text.secondary">Waiting for AI...</Typography>
                </Box>
              )}

              {aiTimedOut && messages.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    AI service is not responding.
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    You can still send messages once the AI service is back online.
                  </Typography>
                </Box>
              )}

              {messages.map((message) => {
                const isUserMessage = message.id.startsWith('user_')
                const isProcessing = message.id.startsWith('processing_')
                const isError = message.type === 'error'

                // System-like messages (processing, success)
                if (isProcessing || message.type === 'success') {
                  return (
                    <Box key={message.id} sx={{ display: 'flex', justifyContent: 'center', my: 0.5 }}>
                      <Typography variant="caption" sx={{
                        fontStyle: 'italic',
                        color: '#9ca3af',
                        fontSize: '0.75rem',
                        px: 1.5,
                        py: 0.5,
                      }}>
                        {message.content}
                      </Typography>
                    </Box>
                  )
                }

                // Error messages
                if (isError) {
                  return (
                    <Box key={message.id} sx={{ display: 'flex', justifyContent: 'center', my: 0.5 }}>
                      <Paper elevation={0} sx={{
                        p: 2,
                        maxWidth: '90%',
                        backgroundColor: '#fef2f2',
                        border: '1px solid #fecaca',
                        borderRadius: 2.5,
                      }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          <ErrorOutlineIcon sx={{ fontSize: 18, color: '#dc2626' }} />
                          <Typography variant="body2" sx={{ fontWeight: 600, color: '#dc2626' }}>
                            Something went wrong
                          </Typography>
                        </Box>
                        <Typography variant="body2" sx={{ color: '#991b1b' }}>
                          {message.content}
                        </Typography>
                      </Paper>
                    </Box>
                  )
                }

                // User and AI message bubbles
                return (
                  <Box
                    key={message.id}
                    sx={{
                      display: 'flex',
                      justifyContent: isUserMessage ? 'flex-end' : 'flex-start',
                      mb: 0.5,
                    }}
                  >
                    <Paper
                      elevation={0}
                      sx={{
                        px: 2,
                        py: 1.5,
                        maxWidth: '80%',
                        borderRadius: isUserMessage
                          ? '16px 16px 4px 16px'
                          : '16px 16px 16px 4px',
                        backgroundColor: isUserMessage ? '#1976d2' : '#f5f5f5',
                        color: isUserMessage ? '#ffffff' : '#1f2937',
                        border: isUserMessage ? 'none' : '1px solid #ebebeb',
                        boxShadow: isUserMessage
                          ? '0 1px 3px rgba(25,118,210,0.2)'
                          : '0 1px 3px rgba(0,0,0,0.04)',
                      }}
                    >
                      <Typography variant="body2" sx={{ lineHeight: 1.5, fontSize: '0.875rem' }}>
                        {message.content}
                      </Typography>
                      <Typography variant="caption" sx={{
                        display: 'block',
                        mt: 0.5,
                        color: isUserMessage ? 'rgba(255,255,255,0.7)' : '#9ca3af',
                        fontSize: '0.65rem',
                      }}>
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </Typography>
                    </Paper>
                  </Box>
                )
              })}

              <div ref={chatEndRef} />
            </Box>

            {/* Input Area */}
            <Box sx={{
              p: 2,
              borderTop: '1px solid #e5e7eb',
              backgroundColor: '#ffffff',
              display: 'flex',
              flexDirection: 'column',
              gap: 1.5,
            }}>
              <Box sx={{
                display: 'flex',
                gap: 1,
                alignItems: 'flex-end',
                backgroundColor: '#f9fafb',
                borderRadius: 3,
                border: '1px solid #e5e7eb',
                boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                px: 2,
                py: 1,
                transition: 'border-color 0.2s, box-shadow 0.2s',
                '&:focus-within': {
                  borderColor: '#1976d2',
                  boxShadow: '0 2px 8px rgba(25,118,210,0.12)',
                },
              }}>
                <TextField
                  fullWidth
                  placeholder={isBuilding ? "Building in progress..." : "Request changes (e.g., 'Make it darker')"}
                  value={userMessage}
                  onChange={(e) => setUserMessage(e.target.value)}
                  disabled={isSending}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSendMessage()
                    }
                  }}
                  size="small"
                  variant="standard"
                  sx={{
                    '& .MuiInput-root': {
                      fontSize: '0.875rem',
                      py: 0.5,
                      '&:before, &:after': { display: 'none' },
                    },
                    '& .MuiInputBase-input': {
                      padding: '8px 0',
                    },
                  }}
                />
                <IconButton
                  onClick={handleSendMessage}
                  disabled={!userMessage.trim() || isSending}
                  sx={{
                    backgroundColor: !userMessage.trim() || isSending ? '#e5e7eb' : '#1976d2',
                    color: !userMessage.trim() || isSending ? '#9ca3af' : '#ffffff',
                    width: 36,
                    height: 36,
                    borderRadius: 2,
                    flexShrink: 0,
                    '&:hover': {
                      backgroundColor: !userMessage.trim() || isSending ? '#e5e7eb' : '#1565c0',
                    },
                    '&.Mui-disabled': {
                      backgroundColor: '#e5e7eb',
                      color: '#9ca3af',
                    },
                  }}
                >
                  <SendIcon sx={{ fontSize: 18 }} />
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
