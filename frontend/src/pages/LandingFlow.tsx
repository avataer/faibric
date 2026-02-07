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
  { label: 'Restaurant', icon: RestaurantIcon, prompt: 'Modern restaurant website with menu, reservations, and photo gallery', color: '#ef4444', desc: 'Menu, bookings & gallery' },
  { label: 'Portfolio', icon: BrushIcon, prompt: 'Creative portfolio for a designer with project showcase and contact form', color: '#8b5cf6', desc: 'Showcase your work' },
  { label: 'SaaS Landing', icon: RocketLaunchIcon, prompt: 'SaaS landing page with pricing tiers, features, and signup form', color: '#1976d2', desc: 'Pricing, features & signup' },
  { label: 'Blog', icon: ArticleIcon, prompt: 'Tech blog with article cards, categories, and newsletter signup', color: '#10b981', desc: 'Articles & newsletter' },
  { label: 'E-commerce', icon: StorefrontIcon, prompt: 'Fashion store with product grid, cart, and checkout', color: '#f59e0b', desc: 'Products, cart & checkout' },
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
      background: '#ffffff',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Subtle decorative elements */}
      <Box sx={{
        position: 'absolute',
        top: '-15%',
        right: '-10%',
        width: '40vw',
        height: '40vw',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(25,118,210,0.04) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />
      <Box sx={{
        position: 'absolute',
        bottom: '-10%',
        left: '-8%',
        width: '35vw',
        height: '35vw',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(25,118,210,0.03) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <Container maxWidth="md" sx={{ position: 'relative', zIndex: 1 }}>
        {/* Hero Section */}
        <Fade in={visible} timeout={800}>
          <Box sx={{
            textAlign: 'center',
            pt: { xs: 8, md: 12 },
            pb: { xs: 3, md: 5 },
          }}>
            <Chip
              icon={<AutoAwesomeIcon sx={{ fontSize: 14 }} />}
              label="AI-Powered Website Builder"
              sx={{
                mb: 3,
                backgroundColor: '#e3f2fd',
                color: '#1565c0',
                border: '1px solid #bbdefb',
                fontWeight: 500,
                fontSize: '0.78rem',
                letterSpacing: '0.04em',
                height: 30,
                '& .MuiChip-icon': { color: '#1976d2' },
                '& .MuiChip-label': { px: 1.5 },
              }}
            />
            <Typography
              variant="h1"
              sx={{
                fontSize: { xs: '2.5rem', sm: '3.5rem', md: '4.2rem' },
                fontWeight: 800,
                lineHeight: 1.08,
                mb: 2.5,
                color: '#1a1a2e',
                letterSpacing: '-0.035em',
              }}
            >
              Describe it.{' '}
              <Box component="span" sx={{
                color: '#1976d2',
              }}>
                We build it.
              </Box>
            </Typography>
            <Typography
              variant="h5"
              sx={{
                color: '#6b7280',
                fontWeight: 400,
                fontSize: { xs: '1rem', sm: '1.1rem', md: '1.2rem' },
                maxWidth: 520,
                mx: 'auto',
                lineHeight: 1.7,
                letterSpacing: '0.01em',
              }}
            >
              Turn your idea into a live, deployed website in under a minute.
              Just describe what you want&mdash;AI handles the rest.
            </Typography>
          </Box>
        </Fade>

        {showUpgradePrompt && (
          <Card sx={{
            mb: 3,
            p: 3,
            textAlign: 'center',
            border: '1px solid #bbdefb',
            backgroundColor: '#f8f9fa',
            boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
            borderRadius: 3,
          }}>
            <Typography variant="h6" sx={{ color: '#1a1a2e', fontWeight: 600, mb: 1 }}>
              Plan Limit Reached
            </Typography>
            <Typography variant="body2" sx={{ color: '#6b7280', mb: 2 }}>
              {error}
            </Typography>
            <Button
              variant="contained"
              onClick={() => navigate('/pricing')}
              sx={{
                background: '#1976d2',
                '&:hover': { background: '#1565c0' },
                textTransform: 'none',
                borderRadius: 2,
                fontWeight: 600,
              }}
            >
              View Pricing Plans
            </Button>
          </Card>
        )}

        {error && !showUpgradePrompt && (
          <Alert severity="error" sx={{
            mb: 3,
            borderRadius: 2,
          }}>
            {error}
          </Alert>
        )}

        {/* Step 1: Enter Request */}
        {step === 'input' && (
          <Fade in={visible} timeout={1000}>
            <Box>
              {/* Main input card */}
              <Box sx={{
                borderRadius: 4,
                mb: 4,
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                boxShadow: '0 4px 24px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04)',
                p: { xs: 3, md: 5 },
              }}>
                <Typography variant="h5" sx={{
                  color: '#1a1a2e',
                  fontWeight: 700,
                  mb: 0.5,
                  fontSize: { xs: '1.2rem', md: '1.5rem' },
                  letterSpacing: '-0.01em',
                }}>
                  What do you want to build?
                </Typography>
                <Typography variant="body2" sx={{
                  color: '#9ca3af',
                  mb: 3,
                  fontSize: '0.88rem',
                }}>
                  Describe your website in plain English. Be as detailed as you like.
                </Typography>

                <Box sx={{
                  position: 'relative',
                  mb: 3,
                  borderRadius: 3,
                  border: '2px solid #e5e7eb',
                  transition: 'all 0.3s ease',
                  '&:focus-within': {
                    borderColor: '#1976d2',
                    boxShadow: '0 0 0 3px rgba(25,118,210,0.1)',
                  },
                }}>
                  <TextField
                    multiline
                    rows={5}
                    fullWidth
                    placeholder="A modern portfolio website for a freelance photographer with a full-screen gallery, booking form, and about section..."
                    value={request}
                    onChange={(e) => {
                      if (!typingStartRef.current) typingStartRef.current = Date.now()
                      setRequest(e.target.value)
                    }}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        backgroundColor: '#fafbfc',
                        borderRadius: 2.8,
                        color: '#1a1a2e',
                        fontSize: '1rem',
                        lineHeight: 1.7,
                        '& fieldset': {
                          border: 'none',
                        },
                        '&:hover fieldset': {
                          border: 'none',
                        },
                        '&.Mui-focused fieldset': {
                          border: 'none',
                        },
                      },
                      '& .MuiOutlinedInput-input::placeholder': {
                        color: '#9ca3af',
                        opacity: 1,
                      },
                    }}
                  />
                </Box>

                {/* Quick Start Templates */}
                <Box sx={{ mb: 4 }}>
                  <Typography variant="caption" sx={{
                    color: '#9ca3af',
                    mb: 2,
                    display: 'block',
                    fontSize: '0.7rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em',
                    fontWeight: 600,
                  }}>
                    Or start from a template
                  </Typography>
                  <Box sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(3, 1fr)', md: 'repeat(5, 1fr)' },
                    gap: 1.5,
                  }}>
                    {TEMPLATES.map((template) => {
                      const IconComponent = template.icon
                      const isSelected = request === template.prompt
                      return (
                        <Box
                          key={template.label}
                          onClick={() => setRequest(template.prompt)}
                          sx={{
                            cursor: 'pointer',
                            borderRadius: 3,
                            p: 2,
                            textAlign: 'center',
                            backgroundColor: isSelected ? `${template.color}08` : '#f8f9fa',
                            border: `1px solid ${isSelected ? template.color : '#e5e7eb'}`,
                            transition: 'all 0.2s ease',
                            '&:hover': {
                              backgroundColor: `${template.color}06`,
                              borderColor: template.color,
                              transform: 'translateY(-2px)',
                              boxShadow: `0 4px 16px ${template.color}18`,
                            },
                          }}
                        >
                          {/* Mini website preview mockup */}
                          <Box sx={{
                            width: '100%',
                            height: 48,
                            borderRadius: 1.5,
                            mb: 1.2,
                            position: 'relative',
                            overflow: 'hidden',
                            backgroundColor: '#ffffff',
                            border: `1px solid ${template.color}20`,
                          }}>
                            {/* Mock browser bar */}
                            <Box sx={{
                              height: 10,
                              backgroundColor: `${template.color}10`,
                              borderBottom: `1px solid ${template.color}15`,
                              display: 'flex',
                              alignItems: 'center',
                              px: 0.5,
                              gap: 0.3,
                            }}>
                              <Box sx={{ width: 3, height: 3, borderRadius: '50%', backgroundColor: `${template.color}40` }} />
                              <Box sx={{ width: 3, height: 3, borderRadius: '50%', backgroundColor: `${template.color}30` }} />
                              <Box sx={{ width: 3, height: 3, borderRadius: '50%', backgroundColor: `${template.color}20` }} />
                            </Box>
                            {/* Mock content */}
                            <Box sx={{ p: 0.5, display: 'flex', flexDirection: 'column', gap: 0.3 }}>
                              <Box sx={{ width: '60%', height: 3, borderRadius: 1, backgroundColor: `${template.color}25` }} />
                              <Box sx={{ width: '80%', height: 2, borderRadius: 1, backgroundColor: '#e5e7eb' }} />
                              <Box sx={{ width: '45%', height: 2, borderRadius: 1, backgroundColor: '#e5e7eb' }} />
                              <Box sx={{ display: 'flex', gap: 0.3, mt: 0.3 }}>
                                <Box sx={{ width: '30%', height: 8, borderRadius: 0.5, backgroundColor: `${template.color}12` }} />
                                <Box sx={{ width: '30%', height: 8, borderRadius: 0.5, backgroundColor: `${template.color}08` }} />
                              </Box>
                            </Box>
                          </Box>
                          <Typography sx={{
                            color: '#1a1a2e',
                            fontSize: '0.82rem',
                            fontWeight: 600,
                            mb: 0.3,
                            lineHeight: 1.2,
                          }}>
                            {template.label}
                          </Typography>
                          <Typography sx={{
                            color: '#9ca3af',
                            fontSize: '0.68rem',
                            lineHeight: 1.3,
                            display: { xs: 'none', sm: 'block' },
                          }}>
                            {template.desc}
                          </Typography>
                        </Box>
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
                    py: 2,
                    fontSize: '1.08rem',
                    fontWeight: 600,
                    borderRadius: 3,
                    textTransform: 'none',
                    background: '#1976d2',
                    boxShadow: '0 4px 14px rgba(25,118,210,0.3)',
                    transition: 'all 0.25s ease',
                    '&:hover': {
                      background: '#1565c0',
                      boxShadow: '0 6px 20px rgba(25,118,210,0.4)',
                      transform: 'translateY(-1px)',
                    },
                    '&:active': {
                      transform: 'translateY(0)',
                    },
                    '&.Mui-disabled': {
                      background: '#e0e0e0',
                      color: '#9ca3af',
                      boxShadow: 'none',
                    },
                  }}
                >
                  {loading ? (
                    <CircularProgress size={24} sx={{ color: '#ffffff' }} />
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
                  alignItems: 'center',
                  gap: { xs: 2, md: 1 },
                  pb: 8,
                  flexDirection: { xs: 'column', sm: 'row' },
                }}>
                  {STATS.map((stat, index) => {
                    const IconComponent = stat.icon
                    return (
                      <Box key={stat.label} sx={{ display: 'flex', alignItems: 'center', gap: 0 }}>
                        <Box sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 1.2,
                          px: { xs: 2.5, md: 3 },
                          py: 1.5,
                          borderRadius: 3,
                          backgroundColor: '#f8f9fa',
                          border: '1px solid #e5e7eb',
                        }}>
                          <Box sx={{
                            width: 32,
                            height: 32,
                            borderRadius: 2,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            backgroundColor: '#e3f2fd',
                          }}>
                            <IconComponent sx={{ fontSize: 16, color: '#1976d2' }} />
                          </Box>
                          <Box>
                            <Typography sx={{
                              color: '#1a1a2e',
                              fontWeight: 700,
                              fontSize: '1.1rem',
                              lineHeight: 1.2,
                            }}>
                              {stat.value}
                            </Typography>
                            <Typography sx={{
                              color: '#9ca3af',
                              fontSize: '0.7rem',
                              letterSpacing: '0.02em',
                            }}>
                              {stat.label}
                            </Typography>
                          </Box>
                        </Box>
                        {index < STATS.length - 1 && (
                          <Box sx={{
                            width: '1px',
                            height: 24,
                            backgroundColor: '#e5e7eb',
                            mx: 1,
                            display: { xs: 'none', sm: 'block' },
                          }} />
                        )}
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
              borderRadius: 4,
              maxWidth: 480,
              mx: 'auto',
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
              p: { xs: 3, md: 5 },
              textAlign: 'center',
            }}>
              <Typography variant="h5" sx={{ color: '#1a1a2e', fontWeight: 600, mb: 1 }}>
                Enter your email to create your account
              </Typography>
              <Typography variant="body2" sx={{ color: '#6b7280', mb: 3 }}>
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
                    backgroundColor: '#f8f9fa',
                    borderRadius: 3,
                    color: '#1a1a2e',
                    '& fieldset': { borderColor: '#e5e7eb' },
                    '&:hover fieldset': { borderColor: '#1976d2' },
                    '&.Mui-focused fieldset': { borderColor: '#1976d2', borderWidth: 2 },
                  },
                  '& .MuiOutlinedInput-input::placeholder': {
                    color: '#9ca3af',
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
                  background: '#1976d2',
                  '&:hover': { background: '#1565c0' },
                  '&.Mui-disabled': { background: '#e0e0e0', color: '#9ca3af' },
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
              borderRadius: 4,
              maxWidth: 480,
              mx: 'auto',
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
              p: { xs: 3, md: 5 },
              textAlign: 'center',
            }}>
              <Box sx={{ mb: 3 }}>
                <CircularProgress size={48} sx={{ color: '#1976d2' }} />
              </Box>
              <Typography variant="h5" sx={{ color: '#1a1a2e', fontWeight: 600, mb: 1 }}>
                Check your email
              </Typography>
              <Typography variant="body1" sx={{ color: '#374151', mb: 2 }}>
                We sent a magic link to <strong>{email}</strong>
              </Typography>
              <Typography variant="body2" sx={{ color: '#9ca3af', mb: 3 }}>
                Click the link in your email to start building your app.
              </Typography>

              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleResendEmail}
                  disabled={resending}
                  sx={{
                    borderColor: '#e5e7eb',
                    color: '#374151',
                    textTransform: 'none',
                    '&:hover': { borderColor: '#1976d2', backgroundColor: '#e3f2fd' },
                  }}
                >
                  {resending ? 'Sending...' : 'Resend Email'}
                </Button>
                <Button
                  variant="text"
                  size="small"
                  onClick={() => setEmailDialogOpen(true)}
                  sx={{
                    color: '#6b7280',
                    textTransform: 'none',
                    '&:hover': { color: '#1976d2' },
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
              backgroundColor: '#ffffff',
              border: '1px solid #e5e7eb',
              borderRadius: 3,
            },
          }}
        >
          <DialogTitle sx={{ color: '#1a1a2e' }}>Change Email Address</DialogTitle>
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
                  color: '#1a1a2e',
                  '& fieldset': { borderColor: '#e5e7eb' },
                  '&:hover fieldset': { borderColor: '#1976d2' },
                  '&.Mui-focused fieldset': { borderColor: '#1976d2' },
                },
                '& .MuiInputLabel-root': { color: '#6b7280' },
                '& .MuiInputLabel-root.Mui-focused': { color: '#1976d2' },
              }}
            />
          </DialogContent>
          <DialogActions>
            <Button
              onClick={() => setEmailDialogOpen(false)}
              sx={{ color: '#6b7280', textTransform: 'none' }}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleChangeEmail}
              disabled={loading || !newEmail.trim()}
              sx={{
                textTransform: 'none',
                background: '#1976d2',
                '&:hover': { background: '#1565c0' },
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
