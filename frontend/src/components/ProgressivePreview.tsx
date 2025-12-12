import { Box, Typography } from '@mui/material'
import { useEffect, useState } from 'react'

interface ProgressivePreviewProps {
  progress: number
  phase: string
  projectName?: string
}

/**
 * Shows an exciting, animated preview that builds up visually
 * as the AI generates the app - like watching a painting come to life
 */
const ProgressivePreview = ({ progress, phase, projectName }: ProgressivePreviewProps) => {
  const [showHeader, setShowHeader] = useState(false)
  const [showHero, setShowHero] = useState(false)
  const [showFeatures, setShowFeatures] = useState(false)
  const [showContent, setShowContent] = useState(false)
  const [showFooter, setShowFooter] = useState(false)
  const [colorPhase, setColorPhase] = useState(0)

  // Progressive reveal based on build progress
  useEffect(() => {
    if (progress >= 10) setShowHeader(true)
    if (progress >= 25) setShowHero(true)
    if (progress >= 40) setShowFeatures(true)
    if (progress >= 55) setShowContent(true)
    if (progress >= 70) setShowFooter(true)
    
    // Color phases
    if (progress >= 60) setColorPhase(1)
    if (progress >= 75) setColorPhase(2)
    if (progress >= 90) setColorPhase(3)
  }, [progress])

  // Dynamic gradient based on progress
  const getBackground = () => {
    if (colorPhase >= 3) return 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    if (colorPhase >= 2) return 'linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%)'
    if (colorPhase >= 1) return 'linear-gradient(135deg, #fafbfc 0%, #f0f2f5 100%)'
    return '#f8f9fa'
  }

  const getTextColor = () => colorPhase >= 3 ? '#ffffff' : '#1a1a2e'
  const getAccentColor = () => colorPhase >= 2 ? '#667eea' : '#cbd5e1'

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        background: getBackground(),
        transition: 'all 0.8s ease-in-out',
        overflow: 'auto',
        fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          height: 60,
          px: 4,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: colorPhase >= 1 ? '1px solid rgba(0,0,0,0.1)' : 'none',
          opacity: showHeader ? 1 : 0,
          transform: showHeader ? 'translateY(0)' : 'translateY(-20px)',
          transition: 'all 0.6s ease-out',
          backgroundColor: colorPhase >= 2 ? 'rgba(255,255,255,0.9)' : 'transparent',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: '8px',
              background: getAccentColor(),
              transition: 'all 0.5s ease',
            }}
          />
          <Typography
            sx={{
              fontWeight: 600,
              fontSize: 18,
              color: colorPhase >= 3 ? '#1a1a2e' : getTextColor(),
              opacity: colorPhase >= 1 ? 1 : 0.5,
              transition: 'all 0.5s ease',
            }}
          >
            {projectName || 'Your App'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 3 }}>
          {['Home', 'About', 'Services', 'Contact'].map((item, i) => (
            <Box
              key={item}
              sx={{
                width: colorPhase >= 1 ? 'auto' : 60,
                height: 12,
                borderRadius: 6,
                background: colorPhase >= 1 ? 'transparent' : '#e2e8f0',
                opacity: showHeader ? 1 : 0,
                transition: `all 0.4s ease ${i * 0.1}s`,
              }}
            >
              {colorPhase >= 1 && (
                <Typography
                  sx={{
                    fontSize: 14,
                    color: colorPhase >= 3 ? '#1a1a2e' : '#64748b',
                    fontWeight: 500,
                  }}
                >
                  {item}
                </Typography>
              )}
            </Box>
          ))}
        </Box>
      </Box>

      {/* Hero Section */}
      <Box
        sx={{
          py: 10,
          px: 4,
          textAlign: 'center',
          opacity: showHero ? 1 : 0,
          transform: showHero ? 'translateY(0) scale(1)' : 'translateY(40px) scale(0.95)',
          transition: 'all 0.8s ease-out 0.2s',
        }}
      >
        {/* Main Heading */}
        <Box
          sx={{
            width: colorPhase >= 1 ? 'auto' : '60%',
            height: colorPhase >= 1 ? 'auto' : 48,
            background: colorPhase >= 1 ? 'transparent' : '#e2e8f0',
            borderRadius: 8,
            mx: 'auto',
            mb: 3,
            transition: 'all 0.6s ease',
          }}
        >
          {colorPhase >= 1 && (
            <Typography
              variant="h2"
              sx={{
                fontWeight: 700,
                fontSize: { xs: 36, md: 52 },
                color: getTextColor(),
                transition: 'color 0.5s ease',
                lineHeight: 1.2,
              }}
            >
              Welcome to Your
              <br />
              <span style={{ color: colorPhase >= 3 ? '#ffd700' : '#667eea' }}>
                Amazing Website
              </span>
            </Typography>
          )}
        </Box>

        {/* Subtitle */}
        <Box
          sx={{
            width: colorPhase >= 1 ? 'auto' : '40%',
            height: colorPhase >= 1 ? 'auto' : 24,
            background: colorPhase >= 1 ? 'transparent' : '#e2e8f0',
            borderRadius: 6,
            mx: 'auto',
            mb: 4,
            transition: 'all 0.6s ease 0.1s',
          }}
        >
          {colorPhase >= 1 && (
            <Typography
              sx={{
                fontSize: 18,
                color: colorPhase >= 3 ? 'rgba(255,255,255,0.9)' : '#64748b',
                maxWidth: 500,
                mx: 'auto',
              }}
            >
              Professional services tailored just for you. Let's create something extraordinary together.
            </Typography>
          )}
        </Box>

        {/* CTA Button */}
        <Box
          sx={{
            display: 'inline-block',
            px: 4,
            py: 1.5,
            borderRadius: '30px',
            background: colorPhase >= 2 
              ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
              : '#e2e8f0',
            boxShadow: colorPhase >= 2 
              ? '0 10px 40px rgba(102, 126, 234, 0.4)'
              : 'none',
            transform: colorPhase >= 2 ? 'scale(1)' : 'scale(0.95)',
            transition: 'all 0.5s ease',
          }}
        >
          <Typography
            sx={{
              color: colorPhase >= 2 ? '#fff' : 'transparent',
              fontWeight: 600,
              fontSize: 16,
            }}
          >
            Get Started
          </Typography>
        </Box>
      </Box>

      {/* Features Section */}
      <Box
        sx={{
          py: 6,
          px: 4,
          opacity: showFeatures ? 1 : 0,
          transform: showFeatures ? 'translateY(0)' : 'translateY(40px)',
          transition: 'all 0.8s ease-out',
        }}
      >
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: 3,
            maxWidth: 900,
            mx: 'auto',
          }}
        >
          {[
            { icon: '★', title: 'Quality First', desc: 'Excellence in every detail' },
            { icon: '◆', title: 'Fast Delivery', desc: 'Quick turnaround times' },
            { icon: '●', title: '24/7 Support', desc: 'Always here for you' },
          ].map((feature, i) => (
            <Box
              key={i}
              sx={{
                p: 3,
                borderRadius: 3,
                background: colorPhase >= 2 
                  ? 'rgba(255,255,255,0.15)'
                  : '#fff',
                backdropFilter: colorPhase >= 2 ? 'blur(10px)' : 'none',
                boxShadow: colorPhase >= 1 
                  ? '0 4px 20px rgba(0,0,0,0.08)'
                  : 'none',
                textAlign: 'center',
                opacity: showFeatures ? 1 : 0,
                transform: showFeatures ? 'translateY(0)' : 'translateY(20px)',
                transition: `all 0.6s ease ${i * 0.15}s`,
              }}
            >
              <Box
                sx={{
                  width: 50,
                  height: 50,
                  borderRadius: '50%',
                  background: colorPhase >= 2 
                    ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                    : '#f1f5f9',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mx: 'auto',
                  mb: 2,
                  fontSize: 20,
                  color: colorPhase >= 2 ? '#fff' : '#94a3b8',
                  transition: 'all 0.5s ease',
                }}
              >
                {feature.icon}
              </Box>
              {colorPhase >= 1 ? (
                <>
                  <Typography sx={{ fontWeight: 600, mb: 1, color: getTextColor() }}>
                    {feature.title}
                  </Typography>
                  <Typography sx={{ fontSize: 14, color: colorPhase >= 3 ? 'rgba(255,255,255,0.8)' : '#64748b' }}>
                    {feature.desc}
                  </Typography>
                </>
              ) : (
                <>
                  <Box sx={{ width: '70%', height: 16, background: '#e2e8f0', borderRadius: 4, mx: 'auto', mb: 1 }} />
                  <Box sx={{ width: '90%', height: 12, background: '#e2e8f0', borderRadius: 4, mx: 'auto' }} />
                </>
              )}
            </Box>
          ))}
        </Box>
      </Box>

      {/* Content Section */}
      <Box
        sx={{
          py: 6,
          px: 4,
          opacity: showContent ? 1 : 0,
          transform: showContent ? 'translateY(0)' : 'translateY(40px)',
          transition: 'all 0.8s ease-out',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            gap: 4,
            maxWidth: 900,
            mx: 'auto',
            alignItems: 'center',
          }}
        >
          {/* Image placeholder */}
          <Box
            sx={{
              flex: 1,
              height: 250,
              borderRadius: 3,
              background: colorPhase >= 2
                ? 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)'
                : '#e2e8f0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.6s ease',
              overflow: 'hidden',
            }}
          >
            {colorPhase >= 2 && (
              <Typography sx={{ fontSize: 60, opacity: 0.6 }}>🖼️</Typography>
            )}
          </Box>
          
          {/* Text content */}
          <Box sx={{ flex: 1 }}>
            {colorPhase >= 1 ? (
              <>
                <Typography
                  variant="h4"
                  sx={{ fontWeight: 700, mb: 2, color: getTextColor() }}
                >
                  Why Choose Us?
                </Typography>
                <Typography sx={{ color: colorPhase >= 3 ? 'rgba(255,255,255,0.85)' : '#64748b', lineHeight: 1.7 }}>
                  We bring years of expertise and passion to every project. Our commitment to excellence ensures you get the best results possible.
                </Typography>
              </>
            ) : (
              <>
                <Box sx={{ width: '80%', height: 28, background: '#e2e8f0', borderRadius: 4, mb: 2 }} />
                <Box sx={{ width: '100%', height: 14, background: '#e2e8f0', borderRadius: 4, mb: 1 }} />
                <Box sx={{ width: '95%', height: 14, background: '#e2e8f0', borderRadius: 4, mb: 1 }} />
                <Box sx={{ width: '70%', height: 14, background: '#e2e8f0', borderRadius: 4 }} />
              </>
            )}
          </Box>
        </Box>
      </Box>

      {/* Footer */}
      <Box
        sx={{
          py: 4,
          px: 4,
          mt: 4,
          borderTop: colorPhase >= 1 ? '1px solid rgba(0,0,0,0.1)' : 'none',
          opacity: showFooter ? 1 : 0,
          transform: showFooter ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.6s ease-out',
          background: colorPhase >= 2 ? 'rgba(0,0,0,0.05)' : 'transparent',
        }}
      >
        <Box sx={{ textAlign: 'center' }}>
          {colorPhase >= 1 ? (
            <Typography sx={{ color: colorPhase >= 3 ? 'rgba(255,255,255,0.7)' : '#94a3b8', fontSize: 14 }}>
              © 2024 Your Company. All rights reserved.
            </Typography>
          ) : (
            <Box sx={{ width: 200, height: 14, background: '#e2e8f0', borderRadius: 4, mx: 'auto' }} />
          )}
        </Box>
      </Box>

      {/* Floating Progress Indicator */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          background: 'rgba(0,0,0,0.8)',
          color: '#fff',
          px: 3,
          py: 1.5,
          borderRadius: 30,
          fontSize: 14,
          fontWeight: 500,
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}
      >
        <Box
          sx={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: '#4ade80',
            animation: 'pulse 1.5s ease-in-out infinite',
            '@keyframes pulse': {
              '0%, 100%': { opacity: 1, transform: 'scale(1)' },
              '50%': { opacity: 0.5, transform: 'scale(1.2)' },
            },
          }}
        />
        {phase}
      </Box>
    </Box>
  )
}

export default ProgressivePreview
