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
  { label: 'SaaS Landing', icon: RocketLaunchIcon, prompt: 'SaaS landing page with pricing tiers, features, and signup form', color: '#3b82f6', desc: 'Pricing, features & signup' },
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
      background: 'linear-gradient(145deg, #050510 0%, #0c0c2a 25%, #111138 50%, #0c0c2a 75%, #050510 100%)',
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
        background: 'radial-gradient(circle, rgba(99,102,241,0.18) 0%, transparent 70%)',
        filter: 'blur(80px)',
        pointerEvents: 'none',
        animation: 'float 20s ease-in-out infinite',
        '@keyframes float': {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '33%': { transform: 'translate(40px, 20px) scale(1.05)' },
          '66%': { transform: 'translate(-10px, 30px) scale(0.98)' },
        },
      }} />
      <Box sx={{
        position: 'absolute',
        bottom: '-15%',
        right: '-10%',
        width: '45vw',
        height: '45vw',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(139,92,246,0.14) 0%, transparent 70%)',
        filter: 'blur(80px)',
        pointerEvents: 'none',
        animation: 'float2 25s ease-in-out infinite',
        '@keyframes float2': {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '50%': { transform: 'translate(-20px, -30px) scale(1.03)' },
        },
      }} />
      {/* Third accent orb - teal */}
      <Box sx={{
        position: 'absolute',
        top: '40%',
        right: '5%',
        width: '30vw',
        height: '30vw',
        borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%)',
        filter: 'blur(80px)',
        pointerEvents: 'none',
        animation: 'float3 30s ease-in-out infinite',
        '@keyframes float3': {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '50%': { transform: 'translate(-30px, 20px)' },
        },
      }} />

      {/* Subtle grid pattern overlay */}
      <Box sx={{
        position: 'absolute',
        inset: 0,
        backgroundImage: 'radial-gradient(rgba(255,255,255,0.025) 1px, transparent 1px)',
        backgroundSize: '48px 48px',
        pointerEvents: 'none',
      }} />

      {/* Horizontal line accents */}
      <Box sx={{
        position: 'absolute',
        top: '30%',
        left: 0,
        right: 0,
        height: '1px',
        background: 'linear-gradient(90deg, transparent, rgba(99,102,241,0.06), transparent)',
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
                backgroundColor: 'rgba(99,102,241,0.1)',
                color: '#a5b4fc',
                border: '1px solid rgba(99,102,241,0.25)',
                fontWeight: 500,
                fontSize: '0.78rem',
                letterSpacing: '0.04em',
                height: 30,
                '& .MuiChip-icon': { color: '#818cf8' },
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
                background: 'linear-gradient(135deg, #ffffff 0%, #e0e7ff 40%, #c7d2fe 60%, #a5b4fc 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.035em',
              }}
            >
              Describe it.{' '}
              <Box component="span" sx={{
                background: 'linear-gradient(135deg, #818cf8 0%, #6366f1 40%, #a78bfa 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
                We build it.
              </Box>
            </Typography>
            <Typography
              variant="h5"
              sx={{
                color: 'rgba(255,255,255,0.5)',
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
              {/* Main input card */}
              <Box sx={{
                position: 'relative',
                borderRadius: 4,
                p: '1px',
                mb: 4,
                background: 'linear-gradient(145deg, rgba(99,102,241,0.2), rgba(139,92,246,0.1), rgba(255,255,255,0.05))',
              }}>
                <Box sx={{
                  backgroundColor: 'rgba(10,10,30,0.85)',
                  backdropFilter: 'blur(24px)',
                  borderRadius: 3.8,
                  p: { xs: 3, md: 5 },
                }}>
                  <Typography variant="h5" sx={{
                    color: '#ffffff',
                    fontWeight: 700,
                    mb: 0.5,
                    fontSize: { xs: '1.2rem', md: '1.5rem' },
                    letterSpacing: '-0.01em',
                  }}>
                    What do you want to build?
                  </Typography>
                  <Typography variant="body2" sx={{
                    color: 'rgba(255,255,255,0.4)',
                    mb: 3,
                    fontSize: '0.88rem',
                  }}>
                    Describe your website in plain English. Be as detailed as you like.
                  </Typography>

                  <Box sx={{
                    position: 'relative',
                    mb: 3,
                    borderRadius: 3,
                    p: '1px',
                    background: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(255,255,255,0.06))',
                    transition: 'all 0.3s ease',
                    '&:focus-within': {
                      background: 'linear-gradient(135deg, rgba(99,102,241,0.4), rgba(139,92,246,0.3), rgba(99,102,241,0.15))',
                      boxShadow: '0 0 24px rgba(99,102,241,0.12), 0 0 48px rgba(99,102,241,0.06)',
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
                          backgroundColor: 'rgba(5,5,20,0.7)',
                          borderRadius: 2.8,
                          color: '#ffffff',
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
                          color: 'rgba(255,255,255,0.22)',
                          opacity: 1,
                        },
                      }}
                    />
                  </Box>

                  {/* Quick Start Templates */}
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="caption" sx={{
                      color: 'rgba(255,255,255,0.3)',
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
                              backgroundColor: isSelected ? `${template.color}18` : 'rgba(255,255,255,0.03)',
                              border: `1px solid ${isSelected ? `${template.color}40` : 'rgba(255,255,255,0.06)'}`,
                              transition: 'all 0.2s ease',
                              '&:hover': {
                                backgroundColor: `${template.color}12`,
                                borderColor: `${template.color}30`,
                                transform: 'translateY(-2px)',
                                boxShadow: `0 4px 16px ${template.color}15`,
                              },
                            }}
                          >
                            <Box sx={{
                              width: 40,
                              height: 40,
                              borderRadius: 2.5,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              mx: 'auto',
                              mb: 1.2,
                              backgroundColor: `${template.color}15`,
                              border: `1px solid ${template.color}25`,
                            }}>
                              <IconComponent sx={{ fontSize: 20, color: template.color }} />
                            </Box>
                            <Typography sx={{
                              color: 'rgba(255,255,255,0.85)',
                              fontSize: '0.82rem',
                              fontWeight: 600,
                              mb: 0.3,
                              lineHeight: 1.2,
                            }}>
                              {template.label}
                            </Typography>
                            <Typography sx={{
                              color: 'rgba(255,255,255,0.3)',
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
                      background: 'linear-gradient(135deg, #6366f1 0%, #7c3aed 50%, #8b5cf6 100%)',
                      boxShadow: '0 4px 24px rgba(99,102,241,0.35), inset 0 1px 0 rgba(255,255,255,0.1)',
                      transition: 'all 0.25s ease',
                      position: 'relative',
                      overflow: 'hidden',
                      '&::before': {
                        content: '""',
                        position: 'absolute',
                        inset: 0,
                        background: 'linear-gradient(135deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%)',
                        opacity: 0,
                        transition: 'opacity 0.25s ease',
                      },
                      '&:hover': {
                        background: 'linear-gradient(135deg, #4f46e5 0%, #6d28d9 50%, #7c3aed 100%)',
                        boxShadow: '0 8px 32px rgba(99,102,241,0.45), inset 0 1px 0 rgba(255,255,255,0.15)',
                        transform: 'translateY(-1px)',
                        '&::before': {
                          opacity: 1,
                        },
                      },
                      '&:active': {
                        transform: 'translateY(0)',
                      },
                      '&.Mui-disabled': {
                        background: 'rgba(99,102,241,0.15)',
                        color: 'rgba(255,255,255,0.25)',
                        boxShadow: 'none',
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
                          backgroundColor: 'rgba(255,255,255,0.025)',
                          border: '1px solid rgba(255,255,255,0.04)',
                        }}>
                          <Box sx={{
                            width: 32,
                            height: 32,
                            borderRadius: 2,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            backgroundColor: 'rgba(99,102,241,0.1)',
                          }}>
                            <IconComponent sx={{ fontSize: 16, color: '#818cf8' }} />
                          </Box>
                          <Box>
                            <Typography sx={{
                              color: '#ffffff',
                              fontWeight: 700,
                              fontSize: '1.1rem',
                              lineHeight: 1.2,
                            }}>
                              {stat.value}
                            </Typography>
                            <Typography sx={{
                              color: 'rgba(255,255,255,0.35)',
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
                            backgroundColor: 'rgba(255,255,255,0.06)',
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
              position: 'relative',
              borderRadius: 4,
              p: '1px',
              maxWidth: 480,
              mx: 'auto',
              background: 'linear-gradient(145deg, rgba(99,102,241,0.2), rgba(255,255,255,0.05))',
            }}>
              <Box sx={{
                backgroundColor: 'rgba(10,10,30,0.85)',
                backdropFilter: 'blur(24px)',
                borderRadius: 3.8,
                p: { xs: 3, md: 5 },
                textAlign: 'center',
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
            </Box>
          </Fade>
        )}

        {/* Step 3: Verify Email */}
        {step === 'verify' && (
          <Fade in={step === 'verify'}>
            <Box sx={{
              position: 'relative',
              borderRadius: 4,
              p: '1px',
              maxWidth: 480,
              mx: 'auto',
              background: 'linear-gradient(145deg, rgba(99,102,241,0.2), rgba(255,255,255,0.05))',
            }}>
              <Box sx={{
                backgroundColor: 'rgba(10,10,30,0.85)',
                backdropFilter: 'blur(24px)',
                borderRadius: 3.8,
                p: { xs: 3, md: 5 },
                textAlign: 'center',
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
