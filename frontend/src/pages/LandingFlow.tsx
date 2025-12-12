import { useState, useEffect, useRef } from 'react'
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
} from '@mui/material'
// Note: LinearProgress removed - now using BuildingStudio component
import { api } from '../services/api'
import BuildingStudio from '../components/BuildingStudio'

type FlowStep = 'input' | 'email' | 'verify' | 'building' | 'deployed'

// Check if we're in development mode
const isDevelopment = import.meta.env.DEV || window.location.hostname === 'localhost'

interface SessionData {
  session_token: string
  status: string
  build_progress?: number
  deployment_url?: string
}

const LandingFlow = () => {
  // Restore session from localStorage on mount
  const savedSession = typeof window !== 'undefined' ? localStorage.getItem('faibric_session') : null
  const savedState = savedSession ? JSON.parse(savedSession) : null
  
  const [step, setStep] = useState<FlowStep>(savedState?.step || 'input')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Form data
  const [request, setRequest] = useState(savedState?.request || '')
  const [email, setEmail] = useState(savedState?.email || '')
  const [sessionToken, setSessionToken] = useState<string | null>(savedState?.sessionToken || null)
  const [sessionData, setSessionData] = useState<SessionData | null>(savedState?.sessionData || null)
  
  // Typing tracking
  const typingStartRef = useRef<number | null>(null)
  
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
        } catch (err) {
          console.error('Status check failed:', err)
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
        
      const res = await api.post('/api/onboarding/start/', {
        request: request.trim(),
        time_to_type_seconds: timeToType,
      })
      
      setSessionToken(res.data.session_token)
      setStep('email')
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to submit request')
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
    const newEmail = prompt('Enter new email:')
    if (!newEmail || !sessionToken) return
    
    try {
      await api.post('/api/onboarding/email/change/', {
        session_token: sessionToken,
        new_email: newEmail.trim(),
      })
      setEmail(newEmail.trim())
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to change email')
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

        <Stepper activeStep={stepIndex} sx={{ mb: 4 }}>
          <Step>
            <StepLabel>Describe Your Idea</StepLabel>
          </Step>
          <Step>
            <StepLabel>Create Account</StepLabel>
          </Step>
          <Step>
            <StepLabel>Build</StepLabel>
          </Step>
          <Step>
            <StepLabel>Deploy</StepLabel>
          </Step>
        </Stepper>

        {error && (
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
                sx={{ mb: 3 }}
              />
              
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
          <Card>
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="h5" sx={{ color: '#000000', fontWeight: 600, mb: 1 }}>
                Check your email
              </Typography>
              <Typography variant="body1" sx={{ color: '#374151', mb: 2 }}>
                We sent a magic link to <strong>{email}</strong>
              </Typography>
              <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
                Click the link in your email to start building your app.
              </Typography>
              
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'center' }}>
                <Link 
                  component="button" 
                  variant="body2" 
                  onClick={handleChangeEmail}
                  sx={{ cursor: 'pointer', color: '#2563eb' }}
                >
                  Wrong email? Click here to change it
                </Link>
                
                {/* TEMPORARY: Skip verification while email is being configured */}
                {(
                  <Button
                    variant="outlined"
                    size="small"
                    color="warning"
                    onClick={async () => {
                      if (sessionToken) {
                        try {
                          setLoading(true)
                          await api.post('/api/onboarding/build/', { session_token: sessionToken })
                          setStep('building')
                        } catch (err: any) {
                          // In production, this will fail with 403
                          if (err.response?.status === 403) {
                            setError('Email verification required. Check your inbox.')
                          } else {
                            console.error('Failed to start build:', err)
                            setStep('building')
                          }
                        } finally {
                          setLoading(false)
                        }
                      }
                    }}
                    sx={{ mt: 2 }}
                    disabled={loading}
                  >
                    {loading ? <CircularProgress size={20} /> : 'Skip & Start Building →'}
                  </Button>
                )}
              </Box>
            </CardContent>
          </Card>
        )}

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
