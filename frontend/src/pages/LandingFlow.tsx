import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Link,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Fade,
} from '@mui/material'
// Note: LinearProgress removed - now using BuildingStudio component
import { api } from '../services/api'
import BuildingStudio from '../components/BuildingStudio'

type FlowStep = 'input' | 'email' | 'verify' | 'building' | 'deployed'

interface SessionData {
  session_token: string
  status: string
  build_progress?: number
  deployment_url?: string
}

const LandingFlow = () => {
  const navigate = useNavigate()
  // Check for ?clear query param to force-clear session
  const shouldClear = typeof window !== 'undefined' && window.location.search.includes('clear')
  
  // Restore session from localStorage on mount (unless clearing)
  const savedSession = !shouldClear && typeof window !== 'undefined' ? localStorage.getItem('faibric_session') : null
  const savedState = savedSession ? JSON.parse(savedSession) : null
  
  const [step, setStep] = useState<FlowStep>(savedState?.step || 'input')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false)
  
  // Form data
  const [request, setRequest] = useState(savedState?.request || '')
  const [email, setEmail] = useState(savedState?.email || '')
  const [sessionToken, setSessionToken] = useState<string | null>(savedState?.sessionToken || null)
  const [sessionData, setSessionData] = useState<SessionData | null>(savedState?.sessionData || null)

  // Email change dialog
  const [emailDialogOpen, setEmailDialogOpen] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [resending, setResending] = useState(false)

  // Typing tracking
  const typingStartRef = useRef<number | null>(null)
  
  // Clear on mount if ?clear param present
  useEffect(() => {
    if (shouldClear) {
      localStorage.removeItem('faibric_session')
      // Remove ?clear from URL without reload
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [shouldClear])
  
  // Persist session state to localStorage
  useEffect(() => {
    if (sessionToken) {
      localStorage.setItem('faibric_session', JSON.stringify({
        step,
        request,
        email,
        sessionToken,
        sessionData
      }))
    }
  }, [step, request, email, sessionToken, sessionData])
  
  // Clear session when starting fresh
  const clearSession = () => {
    localStorage.removeItem('faibric_session')
    setStep('input')
    setRequest('')
    setEmail('')
    setSessionToken(null)
    setSessionData(null)
  }
  
  // Poll for build status
  useEffect(() => {
    if (step === 'building' && sessionToken) {
      const interval = setInterval(async () => {
        try {
          const res = await api.get(`/api/onboarding/status/${sessionToken}/`)
          setSessionData(res.data)
          
          if (res.data.status === 'deployed') {
            setStep('deployed')
            clearInterval(interval)
          }
        } catch {
          // Status check failed - will retry on next interval
        }
      }, 3000)
      
      return () => clearInterval(interval)
    }
  }, [step, sessionToken])

  // Activity heartbeat
  useEffect(() => {
    if (sessionToken) {
      const interval = setInterval(() => {
        api.post('/api/onboarding/activity/', { 
          session_token: sessionToken, 
          event_type: 'heartbeat' 
        }).catch(() => {})
      }, 30000)
      
      return () => clearInterval(interval)
    }
  }, [sessionToken])

  const handleRequestSubmit = async () => {
    if (!request.trim()) return

    setLoading(true)
    setError(null)

    try {
      const timeToType = typingStartRef.current
        ? Math.floor((Date.now() - typingStartRef.current) / 1000)
        : null

      // DEV MODE: Skip email verification, go directly to building
      const res = await api.post('/api/onboarding/start-dev/', {
        request: request.trim(),
        time_to_type_seconds: timeToType,
      })

      setSessionToken(res.data.session_token)
      setStep('building')  // Skip email/verify, go directly to building
    } catch (err: any) {
      if (err.response?.status === 402) {
        setShowUpgradePrompt(true)
        setError(err.response?.data?.message || 'You have reached your plan limit. Upgrade to continue building.')
      } else {
        setError(err.response?.data?.error || 'Failed to submit request')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleEmailSubmit = async () => {
    if (!email.trim() || !sessionToken) return
    
    setLoading(true)
    setError(null)
    
    try {
      await api.post('/api/onboarding/email/', {
        session_token: sessionToken,
        email: email.trim(),
      })
      
      setStep('verify')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to submit email')
    } finally {
      setLoading(false)
    }
  }

  const handleChangeEmail = async () => {
    if (!newEmail.trim() || !sessionToken) return

    setLoading(true)
    try {
      await api.post('/api/onboarding/email/change/', {
        session_token: sessionToken,
        new_email: newEmail.trim(),
      })
      setEmail(newEmail.trim())
      setNewEmail('')
      setEmailDialogOpen(false)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to change email')
    } finally {
      setLoading(false)
    }
  }

  const handleResendEmail = async () => {
    if (!sessionToken) return

    setResending(true)
    try {
      await api.post('/api/onboarding/email/', {
        session_token: sessionToken,
        email: email.trim(),
      })
      setError(null)
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to resend email')
    } finally {
      setResending(false)
    }
  }

  const handleVerify = async (token: string) => {
    setLoading(true)
    try {
      const res = await api.post('/api/onboarding/verify/', {
        magic_token: token,
      })
      
      setSessionData(res.data)
      setStep('building')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Invalid or expired link')
    } finally {
      setLoading(false)
    }
  }

  // Check for magic token in URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    if (token) {
      handleVerify(token)
    }
  }, [])

  const stepIndex = {
    'input': 0,
    'email': 1,
    'verify': 1,
    'building': 2,
    'deployed': 3,
  }[step]

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      backgroundColor: '#ffffff',
      display: 'flex',
      alignItems: 'center',
      py: 8,
    }}>
      <Container maxWidth="md">
        <Box sx={{ textAlign: 'center', mb: 6 }}>
          <Typography variant="h2" sx={{ color: '#000000', fontWeight: 700, mb: 2 }}>
            Faibric
          </Typography>
          <Typography variant="h5" sx={{ color: '#374151' }}>
            Describe what you want to build. We'll make it happen.
          </Typography>
        </Box>

        {/* Stepper hidden in dev mode */}

        {showUpgradePrompt && (
          <Card sx={{ mb: 3, p: 3, textAlign: 'center', border: '2px solid #1976d2' }}>
            <Typography variant="h6" sx={{ color: '#000000', fontWeight: 600, mb: 1 }}>
              Plan Limit Reached
            </Typography>
            <Typography variant="body2" sx={{ color: '#374151', mb: 2 }}>
              {error}
            </Typography>
            <Button variant="contained" onClick={() => navigate('/pricing')}>
              View Pricing Plans
            </Button>
          </Card>
        )}

        {error && !showUpgradePrompt && (
          <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>
        )}

        {/* Step 1: Enter Request */}
        {step === 'input' && (
          <Card>
            <CardContent sx={{ p: 4 }}>
              <Typography variant="h5" sx={{ color: '#000000', fontWeight: 600, mb: 1 }}>
                What do you want to build?
              </Typography>
              <Typography variant="body2" sx={{ color: '#374151', mb: 3 }}>
                Describe your app, website, or tool in plain English. Be as detailed as you like.
              </Typography>
              
              <TextField
                multiline
                rows={4}
                fullWidth
                placeholder="E.g., I need a SaaS dashboard with user analytics, subscription management, and Stripe billing..."
                value={request}
                onChange={(e) => {
                  if (!typingStartRef.current) typingStartRef.current = Date.now()
                  setRequest(e.target.value)
                }}
                sx={{ mb: 2 }}
              />

              {/* Quick Start Templates */}
              <Box sx={{ mb: 3 }}>
                <Typography variant="caption" sx={{ color: '#6b7280', mb: 1, display: 'block' }}>
                  Or start with a template:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {[
                    { label: 'Restaurant', prompt: 'Modern restaurant website with menu, reservations, and photo gallery' },
                    { label: 'Portfolio', prompt: 'Creative portfolio for a designer with project showcase and contact form' },
                    { label: 'SaaS Landing', prompt: 'SaaS landing page with pricing tiers, features, and signup form' },
                    { label: 'Blog', prompt: 'Tech blog with article cards, categories, and newsletter signup' },
                    { label: 'E-commerce', prompt: 'Fashion store with product grid, cart, and checkout' },
                  ].map((template) => (
                    <Button
                      key={template.label}
                      variant="outlined"
                      size="small"
                      onClick={() => setRequest(template.prompt)}
                      sx={{
                        borderColor: '#e5e7eb',
                        color: '#374151',
                        '&:hover': { borderColor: '#3b82f6', bgcolor: '#eff6ff' },
                      }}
                    >
                      {template.label}
                    </Button>
                  ))}
                </Box>
              </Box>

              <Button
                variant="contained"
                size="large"
                fullWidth
                onClick={handleRequestSubmit}
                disabled={loading || !request.trim()}
              >
                {loading ? 'Submitting...' : 'Start Building'}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Enter Email */}
        {step === 'email' && (
          <Card>
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="h5" sx={{ color: '#000000', fontWeight: 600, mb: 1 }}>
                Enter your email to create your account
              </Typography>
              <Typography variant="body2" sx={{ color: '#374151', mb: 3 }}>
                We'll send you a magic link to access your project dashboard.
              </Typography>
              
              <TextField
                type="email"
                fullWidth
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                sx={{ mb: 3 }}
              />
              
              <Button
                variant="contained"
                size="large"
                fullWidth
                onClick={handleEmailSubmit}
                disabled={loading || !email.trim()}
              >
                {loading ? 'Sending...' : 'Send Magic Link'}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Verify Email */}
        {step === 'verify' && (
          <Fade in={step === 'verify'}>
            <Card>
              <CardContent sx={{ p: 4, textAlign: 'center' }}>
                <Box sx={{ mb: 3 }}>
                  <CircularProgress size={48} sx={{ color: '#2563eb' }} />
                </Box>
                <Typography variant="h5" sx={{ color: '#000000', fontWeight: 600, mb: 1 }}>
                  Check your email
                </Typography>
                <Typography variant="body1" sx={{ color: '#374151', mb: 2 }}>
                  We sent a magic link to <strong>{email}</strong>
                </Typography>
                <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
                  Click the link in your email to start building your app.
                </Typography>

                <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleResendEmail}
                    disabled={resending}
                  >
                    {resending ? 'Sending...' : 'Resend Email'}
                  </Button>
                  <Button
                    variant="text"
                    size="small"
                    onClick={() => setEmailDialogOpen(true)}
                  >
                    Change Email
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Fade>
        )}

        {/* Email Change Dialog */}
        <Dialog open={emailDialogOpen} onClose={() => setEmailDialogOpen(false)}>
          <DialogTitle>Change Email Address</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              fullWidth
              type="email"
              label="New Email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              sx={{ mt: 1 }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setEmailDialogOpen(false)}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleChangeEmail}
              disabled={loading || !newEmail.trim()}
            >
              {loading ? 'Updating...' : 'Update Email'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Step 4 & 5: Building and Deployed - Stay in split-screen view */}
        {(step === 'building' || step === 'deployed') && sessionToken && (
          <Box sx={{ 
            position: 'fixed', 
            top: 0, 
            left: 0, 
            right: 0, 
            bottom: 0, 
            zIndex: 1000 
          }}>
            <BuildingStudio
              sessionToken={sessionToken}
              initialRequest={request}
              onDeployed={(url) => {
                setSessionData(prev => prev ? { ...prev, deployment_url: url } : { session_token: sessionToken, status: 'deployed', deployment_url: url })
                // Stay in building view - don't switch to deployed card
              }}
              onNewProject={clearSession}
            />
          </Box>
        )}
      </Container>
    </Box>
  )
}

export default LandingFlow
