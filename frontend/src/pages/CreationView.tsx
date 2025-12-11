import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Paper,
  LinearProgress,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import { projectsService } from '../services/projects'

interface ThinkingStep {
  timestamp: string
  message: string
  type: 'thinking' | 'success' | 'error'
  details?: string
}

const CreationView = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<any>(null)
  const [progress, setProgress] = useState<any>(null)
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([])
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    if (!id) return

    loadProject()

    // Poll for progress
    const interval = setInterval(async () => {
      try {
        const progressData = await projectsService.getProgress(Number(id))
        setProgress(progressData)

        // Add thinking step
        if (progressData.message) {
          setThinkingSteps(prev => {
            const lastStep = prev[prev.length - 1]
            if (!lastStep || lastStep.message !== progressData.message) {
              return [
                ...prev,
                {
                  timestamp: new Date().toLocaleTimeString(),
                  message: progressData.message,
                  type: progressData.progress === 100 ? 'success' : 'thinking',
                },
              ]
            }
            return prev
          })
        }

        // Check if complete
        const updatedProject = await projectsService.getProject(Number(id))
        setProject(updatedProject)

        if (updatedProject.status === 'ready') {
          setIsComplete(true)
          clearInterval(interval)
          setTimeout(() => {
            navigate(`/projects/${id}`)
          }, 2000)
        } else if (updatedProject.status === 'failed') {
          clearInterval(interval)
        }
      } catch (error) {
        console.error('Failed to get progress:', error)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [id, navigate])

  const loadProject = async () => {
    try {
      const data = await projectsService.getProject(Number(id))
      setProject(data)
    } catch (error) {
      console.error('Failed to load project:', error)
    }
  }

  if (!project) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Typography>Loading...</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden', bgcolor: '#0a0e1a' }}>
      {/* Left Sidebar - Thinking Process */}
      <Box
        sx={{
          width: 320,
          bgcolor: '#f8f9fa',
          borderRight: '1px solid #e0e0e0',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <Box sx={{ p: 3, bgcolor: 'white', borderBottom: '1px solid #e0e0e0' }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            {project.name}
          </Typography>
          <Typography variant="h6" fontWeight={600}>
            {isComplete ? '✨ Generation Complete!' : 'Thought for 5s'}
          </Typography>
        </Box>

        {/* Thinking Steps */}
        <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 2, color: '#666' }}>
            Planning Your {project.name}
          </Typography>

          {thinkingSteps.map((step, index) => (
            <Box key={index} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                {step.type === 'success' ? (
                  <CheckCircleIcon sx={{ fontSize: 18, color: '#10b981', mt: 0.3 }} />
                ) : (
                  <Box
                    sx={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      bgcolor: '#3b82f6',
                      mt: 1,
                    }}
                  />
                )}
                <Box sx={{ flex: 1 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      color: step.type === 'success' ? '#10b981' : '#374151',
                      fontWeight: step.type === 'success' ? 600 : 400,
                      lineHeight: 1.5,
                    }}
                  >
                    {step.message}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {step.timestamp}
                  </Typography>
                </Box>
              </Box>
            </Box>
          ))}

          {!isComplete && progress && (
            <Box sx={{ mt: 3, p: 2, bgcolor: '#f0f7ff', borderRadius: 2 }}>
              <Typography variant="caption" color="primary" fontWeight={600}>
                Used 6 tools
              </Typography>
              <Divider sx={{ my: 1 }} />
              <Typography variant="caption" color="text.secondary">
                Analyzing requirements, generating schema, creating components...
              </Typography>
            </Box>
          )}
        </Box>

        {/* Progress Bar */}
        {!isComplete && progress && (
          <Box sx={{ p: 2, bgcolor: 'white', borderTop: '1px solid #e0e0e0' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="caption" fontWeight={600}>
                Progress
              </Typography>
              <Typography variant="caption" color="primary" fontWeight={600}>
                {progress.progress}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={progress.progress}
              sx={{
                height: 6,
                borderRadius: 3,
                bgcolor: '#e3f2fd',
                '& .MuiLinearProgress-bar': {
                  bgcolor: '#2196f3',
                  borderRadius: 3,
                },
              }}
            />
          </Box>
        )}
      </Box>

      {/* Right Panel - Preview */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top Bar */}
        <Box
          sx={{
            height: 60,
            bgcolor: '#0f1419',
            borderBottom: '1px solid #2d3748',
            display: 'flex',
            alignItems: 'center',
            px: 3,
            gap: 2,
          }}
        >
          <Typography variant="body2" sx={{ color: '#9ca3af' }}>
            app.base44.com
          </Typography>
          <Box sx={{ flex: 1 }} />
          <Tooltip title="Refresh Preview">
            <IconButton size="small" sx={{ color: '#9ca3af' }}>
              <RefreshIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Preview Content */}
        <Box
          sx={{
            flex: 1,
            bgcolor: '#0a0e1a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            p: 4,
          }}
        >
          <Paper
            sx={{
              maxWidth: 800,
              width: '100%',
              p: 4,
              bgcolor: '#1a1f2e',
              color: 'white',
              textAlign: 'center',
            }}
          >
            {isComplete ? (
              <>
                <Typography variant="h4" gutterBottom sx={{ color: '#10b981' }}>
                  🎉 Your App is Ready!
                </Typography>
                <Typography variant="body1" color="#9ca3af">
                  Redirecting to project details...
                </Typography>
              </>
            ) : (
              <>
                <Typography variant="h3" gutterBottom sx={{ color: '#3b82f6', textTransform: 'uppercase' }}>
                  {project.name}
                </Typography>
                <Divider sx={{ my: 3, borderColor: '#2d3748' }} />
                
                {project.description && (
                  <Typography variant="body1" sx={{ mb: 3, color: '#9ca3af' }}>
                    {project.description}
                  </Typography>
                )}

                <Typography variant="h6" sx={{ mb: 2, color: 'white' }}>
                  Key Features:
                </Typography>
                <Box sx={{ textAlign: 'left', maxWidth: 500, mx: 'auto' }}>
                  {[
                    'Portfolio overview with total value',
                    'Individual stock cards with real-time data',
                    'Add/remove stocks with purchase details',
                    'Visual charts for portfolio distribution',
                    'Color-coded gains/losses',
                  ].map((feature, idx) => (
                    <Typography
                      key={idx}
                      variant="body2"
                      sx={{ mb: 1, color: '#9ca3af', display: 'flex', alignItems: 'center', gap: 1 }}
                    >
                      <Box
                        sx={{
                          width: 6,
                          height: 6,
                          borderRadius: '50%',
                          bgcolor: '#3b82f6',
                        }}
                      />
                      {feature}
                    </Typography>
                  ))}
                </Box>

                {progress && (
                  <Box sx={{ mt: 4 }}>
                    <Typography variant="caption" sx={{ color: '#6b7280' }}>
                      {progress.message}
                    </Typography>
                  </Box>
                )}
              </>
            )}
          </Paper>
        </Box>
      </Box>
    </Box>
  )
}

export default CreationView

