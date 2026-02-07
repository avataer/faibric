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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Fade,
  Chip,
} from '@mui/material'
import RestaurantIcon from '@mui/icons-material/Restaurant'
import BrushIcon from '@mui/icons-material/Brush'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import ArticleIcon from '@mui/icons-material/Article'
import StorefrontIcon from '@mui/icons-material/Storefront'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import GroupsIcon from '@mui/icons-material/Groups'
import WebIcon from '@mui/icons-material/Web'
import BoltIcon from '@mui/icons-material/Bolt'
import { api } from '../services/api'
import BuildingStudio from '../components/BuildingStudio'

type FlowStep = 'input' | 'email' | 'verify' | 'building' | 'deployed'

interface SessionData {
  session_token: string
  status: string
  build_progress?: number
  deployment_url?: string
}

const TEMPLATES = [
  { label: 'Restaurant', icon: RestaurantIcon, prompt: 'Modern restaurant website with menu, reservations, and photo gallery', color: '#ef4444' },
  { label: 'Portfolio', icon: BrushIcon, prompt: 'Creative portfolio for a designer with project showcase and contact form', color: '#8b5cf6' },
  { label: 'SaaS Landing', icon: RocketLaunchIcon, prompt: 'SaaS landing page with pricing tiers, features, and signup form', color: '#3b82f6' },
  { label: 'Blog', icon: ArticleIcon, prompt: 'Tech blog with article cards, categories, and newsletter signup', color: '#10b981' },
  { label: 'E-commerce', icon: StorefrontIcon, prompt: 'Fashion store with product grid, cart, and checkout', color: '#f59e0b' },
]

const STATS = [
  { icon: GroupsIcon, value: '2,500+', label: 'Creators' },
  { icon: WebIcon, value: '10,000+', label: 'Sites Built' },
  { icon: BoltIcon, value: '<60s', label: 'Avg Build Time' },
]

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

  // Fade-in animation state
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 100)
    return () => clearTimeout(timer)
  }, [])

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
      background: 'linear-gradient(145deg, #0a0a1a 0%, #111133 35%, #0d0d2b 65%, #0a0a1a 100%)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Animated gradient orbs */}
      <Box sx={{
        position: 'absolute',
        top: '-20%',
        left: '-10%',
        width: '50vw',
        height: '50vw',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)',
        filter: 'blur(60px)',
        pointerEvents: 'none',
        animation: 'float 20s ease-in-out infinite',
        '@keyframes float': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '50%': { transform: 'translate(30px, 20px)' },
        },
      }} />
      <Box sx={{
        position: 'absolute',
        bottom: '-15%',
        right: '-10%',
        width: '45vw',
        height: '45vw',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)',
        filter: 'blur(60px)',
        pointerEvents: 'none',
        animation: 'float2 25s ease-in-out infinite',
        '@keyframes float2': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '50%': { transform: 'translate(-20px, -30px)' },
        },
      }} />

      {/* Subtle grid pattern overlay */}
      <Box sx={{
        position: 'absolute',
        inset: 0,
        backgroundImage: 'radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
        pointerEvents: 'none',
      }} />

      <Container maxWidth="md" sx={{ position: 'relative', zIndex: 1 }}>
        {/* Hero Section */}
        <Fade in={visible} timeout={800}>
          <Box sx={{
            textAlign: 'center',
            pt: { xs: 8, md: 12 },
            pb: { xs: 4, md: 6 },
          }}>
            <Chip
              icon={<AutoAwesomeIcon sx={{ fontSize: 16 }} />}
              label="AI-Powered Website Builder"
              sx={{
                mb: 3,
                backgroundColor: 'rgba(99,102,241,0.15)',
                color: '#a5b4fc',
                border: '1px solid rgba(99,102,241,0.3)',
                fontWeight: 500,
                fontSize: '0.8rem',
                letterSpacing: '0.02em',
                '& .MuiChip-icon': { color: '#a5b4fc' },
              }}
            />
            <Typography
              variant="h1"
              sx={{
                fontSize: { xs: '2.5rem', sm: '3.5rem', md: '4rem' },
                fontWeight: 800,
                lineHeight: 1.1,
                mb: 2.5,
                background: 'linear-gradient(135deg, #ffffff 0%, #e0e7ff 50%, #a5b4fc 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.03em',
              }}
            >
              Describe it. We build it.
            </Typography>
            <Typography
              variant="h5"
              sx={{
                color: 'rgba(255,255,255,0.55)',
                fontWeight: 400,
                fontSize: { xs: '1rem', sm: '1.15rem', md: '1.25rem' },
                maxWidth: 560,
                mx: 'auto',
                lineHeight: 1.6,
              }}
            >
              Turn your idea into a live, deployed website in under a minute.
              Just describe what you want -- AI handles the rest.
            </Typography>
          </Box>
        </Fade>

        {showUpgradePrompt && (
          <Card sx={{
            mb: 3,
            p: 3,
            textAlign: 'center',
            border: '1px solid rgba(99,102,241,0.4)',
            backgroundColor: 'rgba(15,15,40,0.9)',
            backdropFilter: 'blur(20px)',
          }}>
            <Typography variant="h6" sx={{ color: '#ffffff', fontWeight: 600, mb: 1 }}>
              Plan Limit Reached
            </Typography>
            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', mb: 2 }}>
              {error}
            </Typography>
            <Button
              variant="contained"
              onClick={() => navigate('/pricing')}
              sx={{
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                '&:hover': { background: 'linear-gradient(135deg, #4f46e5, #7c3aed)' },
              }}
            >
              View Pricing Plans
            </Button>
          </Card>
        )}

        {error && !showUpgradePrompt && (
          <Alert severity="error" sx={{
            mb: 3,
            backgroundColor: 'rgba(239,68,68,0.1)',
            border: '1px solid rgba(239,68,68,0.3)',
            color: '#fca5a5',
          }}>
            {error}
          </Alert>
        )}

        {/* Step 1: Enter Request */}
        {step === 'input' && (
          <Fade in={visible} timeout={1000}>
            <Box>
              <Box sx={{
                backgroundColor: 'rgba(255,255,255,0.04)',
                backdropFilter: 'blur(20px)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 4,
                p: { xs: 3, md: 5 },
                mb: 4,
              }}>
                <Typography variant="h5" sx={{
                  color: '#ffffff',
                  fontWeight: 600,
                  mb: 0.5,
                  fontSize: { xs: '1.2rem', md: '1.5rem' },
                }}>
                  What do you want to build?
                </Typography>
                <Typography variant="body2" sx={{
                  color: 'rgba(255,255,255,0.45)',
                  mb: 3,
                  fontSize: '0.9rem',
                }}>
                  Describe your app, website, or tool in plain English. Be as detailed as you like.
                </Typography>

                <TextField
                  multiline
                  rows={4}
                  fullWidth
                  placeholder="A modern portfolio website for a freelance photographer with a full-screen gallery, booking form, and about section..."
                  value={request}
                  onChange={(e) => {
                    if (!typingStartRef.current) typingStartRef.current = Date.now()
                    setRequest(e.target.value)
                  }}
                  sx={{
                    mb: 3,
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: 'rgba(0,0,0,0.3)',
                      borderRadius: 3,
                      color: '#ffffff',
                      fontSize: '1rem',
                      lineHeight: 1.6,
                      transition: 'all 0.2s ease',
                      '& fieldset': {
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                      },
                      '&:hover fieldset': {
                        borderColor: 'rgba(99,102,241,0.4)',
                      },
                      '&.Mui-focused fieldset': {
                        borderColor: 'rgba(99,102,241,0.6)',
                        borderWidth: 1,
                        boxShadow: '0 0 0 3px rgba(99,102,241,0.1)',
                      },
                    },
                    '& .MuiOutlinedInput-input::placeholder': {
                      color: 'rgba(255,255,255,0.25)',
                      opacity: 1,
                    },
                  }}
                />

                {/* Quick Start Templates */}
                <Box sx={{ mb: 3 }}>
                  <Typography variant="caption" sx={{
                    color: 'rgba(255,255,255,0.35)',
                    mb: 1.5,
                    display: 'block',
                    fontSize: '0.75rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                    fontWeight: 600,
                  }}>
                    Quick start from a template
                  </Typography>
                  <Box sx={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 1.5,
                  }}>
                    {TEMPLATES.map((template) => {
                      const IconComponent = template.icon
                      return (
                        <Button
                          key={template.label}
                          variant="outlined"
                          size="small"
                          startIcon={<IconComponent sx={{ fontSize: '18px !important' }} />}
                          onClick={() => setRequest(template.prompt)}
                          sx={{
                            borderColor: 'rgba(255,255,255,0.1)',
                            color: 'rgba(255,255,255,0.7)',
                            borderRadius: 2.5,
                            px: 2,
                            py: 0.8,
                            fontSize: '0.82rem',
                            fontWeight: 500,
                            textTransform: 'none',
                            transition: 'all 0.2s ease',
                            '&:hover': {
                              borderColor: template.color,
                              backgroundColor: `${template.color}15`,
                              color: '#ffffff',
                              transform: 'translateY(-1px)',
                            },
                          }}
                        >
                          {template.label}
                        </Button>
                      )
                    })}
                  </Box>
                </Box>

                <Button
                  variant="contained"
                  size="large"
                  fullWidth
                  onClick={handleRequestSubmit}
                  disabled={loading || !request.trim()}
                  endIcon={loading ? undefined : <ArrowForwardIcon />}
                  sx={{
                    py: 1.8,
                    fontSize: '1.05rem',
                    fontWeight: 600,
                    borderRadius: 3,
                    textTransform: 'none',
                    background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                    boxShadow: '0 4px 20px rgba(99,102,241,0.3)',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                      boxShadow: '0 6px 30px rgba(99,102,241,0.4)',
                      transform: 'translateY(-1px)',
                    },
                    '&.Mui-disabled': {
                      background: 'rgba(99,102,241,0.2)',
                      color: 'rgba(255,255,255,0.3)',
                    },
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} sx={{ color: 'rgba(255,255,255,0.7)' }} />
                  ) : (
                    'Start Building'
                  )}
                </Button>
              </Box>

              {/* Social proof / trust signals */}
              <Fade in={visible} timeout={1400}>
                <Box sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  gap: { xs: 3, md: 6 },
                  pb: 8,
                }}>
                  {STATS.map((stat) => {
                    const IconComponent = stat.icon
                    return (
                      <Box key={stat.label} sx={{ textAlign: 'center' }}>
                        <Box sx={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 0.8,
                          mb: 0.5,
                        }}>
                          <IconComponent sx={{ fontSize: 18, color: 'rgba(165,180,252,0.6)' }} />
                          <Typography variant="h6" sx={{
                            color: '#ffffff',
                            fontWeight: 700,
                            fontSize: { xs: '1.1rem', md: '1.3rem' },
                          }}>
                            {stat.value}
                          </Typography>
                        </Box>
                        <Typography variant="caption" sx={{
                          color: 'rgba(255,255,255,0.35)',
                          fontSize: '0.75rem',
                          letterSpacing: '0.03em',
                        }}>
                          {stat.label}
                        </Typography>
                      </Box>
                    )
                  })}
                </Box>
              </Fade>
            </Box>
          </Fade>
        )}

        {/* Step 2: Enter Email */}
        {step === 'email' && (
          <Fade in timeout={600}>
            <Box sx={{
              backgroundColor: 'rgba(255,255,255,0.04)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 4,
              p: { xs: 3, md: 5 },
              textAlign: 'center',
              maxWidth: 480,
              mx: 'auto',
            }}>
              <Typography variant="h5" sx={{ color: '#ffffff', fontWeight: 600, mb: 1 }}>
                Enter your email to create your account
              </Typography>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.5)', mb: 3 }}>
                We'll send you a magic link to access your project dashboard.
              </Typography>

              <TextField
                type="email"
                fullWidth
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                sx={{
                  mb: 3,
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: 'rgba(0,0,0,0.3)',
                    borderRadius: 3,
                    color: '#ffffff',
                    '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                    '&:hover fieldset': { borderColor: 'rgba(99,102,241,0.4)' },
                    '&.Mui-focused fieldset': { borderColor: 'rgba(99,102,241,0.6)', borderWidth: 1 },
                  },
                  '& .MuiOutlinedInput-input::placeholder': {
                    color: 'rgba(255,255,255,0.25)',
                    opacity: 1,
                  },
                }}
              />

              <Button
                variant="contained"
                size="large"
                fullWidth
                onClick={handleEmailSubmit}
                disabled={loading || !email.trim()}
                sx={{
                  py: 1.5,
                  fontSize: '1rem',
                  fontWeight: 600,
                  borderRadius: 3,
                  textTransform: 'none',
                  background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                  '&:hover': { background: 'linear-gradient(135deg, #4f46e5, #7c3aed)' },
                  '&.Mui-disabled': { background: 'rgba(99,102,241,0.2)', color: 'rgba(255,255,255,0.3)' },
                }}
              >
                {loading ? 'Sending...' : 'Send Magic Link'}
              </Button>
            </Box>
          </Fade>
        )}

        {/* Step 3: Verify Email */}
        {step === 'verify' && (
          <Fade in={step === 'verify'}>
            <Box sx={{
              backgroundColor: 'rgba(255,255,255,0.04)',
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 4,
              p: { xs: 3, md: 5 },
              textAlign: 'center',
              maxWidth: 480,
              mx: 'auto',
            }}>
              <Box sx={{ mb: 3 }}>
                <CircularProgress size={48} sx={{ color: '#818cf8' }} />
              </Box>
              <Typography variant="h5" sx={{ color: '#ffffff', fontWeight: 600, mb: 1 }}>
                Check your email
              </Typography>
              <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.7)', mb: 2 }}>
                We sent a magic link to <strong>{email}</strong>
              </Typography>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.4)', mb: 3 }}>
                Click the link in your email to start building your app.
              </Typography>

              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleResendEmail}
                  disabled={resending}
                  sx={{
                    borderColor: 'rgba(255,255,255,0.15)',
                    color: 'rgba(255,255,255,0.7)',
                    textTransform: 'none',
                    '&:hover': { borderColor: 'rgba(99,102,241,0.5)', backgroundColor: 'rgba(99,102,241,0.1)' },
                  }}
                >
                  {resending ? 'Sending...' : 'Resend Email'}
                </Button>
                <Button
                  variant="text"
                  size="small"
                  onClick={() => setEmailDialogOpen(true)}
                  sx={{
                    color: 'rgba(255,255,255,0.5)',
                    textTransform: 'none',
                    '&:hover': { color: '#a5b4fc' },
                  }}
                >
                  Change Email
                </Button>
              </Box>
            </Box>
          </Fade>
        )}

        {/* Email Change Dialog */}
        <Dialog
          open={emailDialogOpen}
          onClose={() => setEmailDialogOpen(false)}
          PaperProps={{
            sx: {
              backgroundColor: '#1a1a3e',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 3,
            },
          }}
        >
          <DialogTitle sx={{ color: '#ffffff' }}>Change Email Address</DialogTitle>
          <DialogContent>
            <TextField
              autoFocus
              fullWidth
              type="email"
              label="New Email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              sx={{
                mt: 1,
                '& .MuiOutlinedInput-root': {
                  color: '#ffffff',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.15)' },
                  '&:hover fieldset': { borderColor: 'rgba(99,102,241,0.4)' },
                  '&.Mui-focused fieldset': { borderColor: '#6366f1' },
                },
                '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.5)' },
                '& .MuiInputLabel-root.Mui-focused': { color: '#a5b4fc' },
              }}
            />
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => setEmailDialogOpen(false)}
              sx={{ color: 'rgba(255,255,255,0.5)', textTransform: 'none' }}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleChangeEmail}
              disabled={loading || !newEmail.trim()}
              sx={{
                textTransform: 'none',
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                '&:hover': { background: 'linear-gradient(135deg, #4f46e5, #7c3aed)' },
              }}
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
