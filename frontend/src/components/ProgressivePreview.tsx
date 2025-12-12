import { Box, Typography } from '@mui/material'
import { useEffect, useState, useMemo } from 'react'

interface ProgressivePreviewProps {
  progress: number
  phase: string
  projectName?: string
  userRequest?: string
}

// Detect the type of website from the user's request
const detectSiteType = (request: string): {
  type: string
  title: string
  subtitle: string
  features: { icon: string; title: string; desc: string }[]
  ctaText: string
  colors: { primary: string; secondary: string; accent: string }
  contentTitle: string
  contentText: string
} => {
  const r = request.toLowerCase()

  // Stocks / Trading / Finance
  if (r.includes('stock') || r.includes('trad') || r.includes('invest') || r.includes('finance') || r.includes('crypto') || r.includes('market')) {
    return {
      type: 'finance',
      title: 'Smart Trading',
      subtitle: 'Real-time market data and intelligent portfolio management',
      features: [
        { icon: '📈', title: 'Live Charts', desc: 'Real-time market data' },
        { icon: '💹', title: 'Portfolio Tracking', desc: 'Monitor your investments' },
        { icon: '🔔', title: 'Price Alerts', desc: 'Never miss a move' },
      ],
      ctaText: 'Start Trading',
      colors: { primary: '#0f172a', secondary: '#1e40af', accent: '#22c55e' },
      contentTitle: 'Market Insights',
      contentText: 'Advanced analytics and real-time data to power your trading decisions.',
    }
  }

  // Psychology / Therapy / Mental Health
  if (r.includes('psycholog') || r.includes('therap') || r.includes('mental') || r.includes('counsel') || r.includes('coach')) {
    return {
      type: 'therapy',
      title: 'Find Your Balance',
      subtitle: 'Professional support for your mental health journey',
      features: [
        { icon: '🧠', title: 'Expert Care', desc: 'Licensed professionals' },
        { icon: '💚', title: 'Safe Space', desc: 'Confidential sessions' },
        { icon: '📅', title: 'Easy Booking', desc: 'Online scheduling' },
      ],
      ctaText: 'Book Session',
      colors: { primary: '#134e4a', secondary: '#0d9488', accent: '#5eead4' },
      contentTitle: 'Your Wellness Matters',
      contentText: 'Evidence-based therapy approaches tailored to your unique needs.',
    }
  }

  // Hair / Beauty / Salon
  if (r.includes('hair') || r.includes('salon') || r.includes('beauty') || r.includes('stylist') || r.includes('barber')) {
    return {
      type: 'beauty',
      title: 'Style & Elegance',
      subtitle: 'Transform your look with our expert stylists',
      features: [
        { icon: '✂️', title: 'Expert Cuts', desc: 'Precision styling' },
        { icon: '💇', title: 'Color Services', desc: 'Vibrant transformations' },
        { icon: '💅', title: 'Full Treatments', desc: 'Head to toe beauty' },
      ],
      ctaText: 'Book Appointment',
      colors: { primary: '#831843', secondary: '#db2777', accent: '#f9a8d4' },
      contentTitle: 'Your Style, Our Passion',
      contentText: 'Award-winning stylists dedicated to making you look and feel amazing.',
    }
  }

  // Restaurant / Food / Cafe
  if (r.includes('restaurant') || r.includes('food') || r.includes('cafe') || r.includes('menu') || r.includes('chef') || r.includes('dining')) {
    return {
      type: 'restaurant',
      title: 'Culinary Excellence',
      subtitle: 'Exquisite flavors crafted with passion',
      features: [
        { icon: '🍽️', title: 'Fine Dining', desc: 'Elegant atmosphere' },
        { icon: '👨‍🍳', title: 'Master Chefs', desc: 'World-class cuisine' },
        { icon: '🍷', title: 'Wine Selection', desc: 'Curated pairings' },
      ],
      ctaText: 'Reserve Table',
      colors: { primary: '#44403c', secondary: '#a16207', accent: '#fbbf24' },
      contentTitle: 'A Feast for the Senses',
      contentText: 'Fresh, locally-sourced ingredients prepared with culinary artistry.',
    }
  }

  // Fitness / Gym / Health
  if (r.includes('gym') || r.includes('fitness') || r.includes('workout') || r.includes('trainer') || r.includes('yoga')) {
    return {
      type: 'fitness',
      title: 'Unleash Your Potential',
      subtitle: 'Transform your body and mind',
      features: [
        { icon: '💪', title: 'Expert Trainers', desc: 'Personalized coaching' },
        { icon: '🏋️', title: 'Modern Equipment', desc: 'State-of-the-art gym' },
        { icon: '📊', title: 'Track Progress', desc: 'Measurable results' },
      ],
      ctaText: 'Join Now',
      colors: { primary: '#1e1b4b', secondary: '#7c3aed', accent: '#a78bfa' },
      contentTitle: 'Your Fitness Journey',
      contentText: 'Customized training programs designed to help you reach your goals.',
    }
  }

  // Portfolio / Artist / Creative
  if (r.includes('portfolio') || r.includes('artist') || r.includes('design') || r.includes('creative') || r.includes('photographer') || r.includes('nft')) {
    return {
      type: 'portfolio',
      title: 'Creative Vision',
      subtitle: 'Showcasing artistic excellence',
      features: [
        { icon: '🎨', title: 'Unique Style', desc: 'Original creations' },
        { icon: '🖼️', title: 'Gallery', desc: 'Featured works' },
        { icon: '✨', title: 'Commissions', desc: 'Custom projects' },
      ],
      ctaText: 'View Gallery',
      colors: { primary: '#18181b', secondary: '#6366f1', accent: '#c084fc' },
      contentTitle: 'Art That Speaks',
      contentText: 'Each piece tells a story, crafted with passion and precision.',
    }
  }

  // Tech / SaaS / App
  if (r.includes('app') || r.includes('saas') || r.includes('software') || r.includes('tech') || r.includes('platform')) {
    return {
      type: 'tech',
      title: 'The Future is Here',
      subtitle: 'Powerful tools for modern teams',
      features: [
        { icon: '🚀', title: 'Lightning Fast', desc: 'Optimized performance' },
        { icon: '🔒', title: 'Secure', desc: 'Enterprise-grade security' },
        { icon: '🔗', title: 'Integrations', desc: 'Connect everything' },
      ],
      ctaText: 'Get Started',
      colors: { primary: '#0c0a09', secondary: '#2563eb', accent: '#60a5fa' },
      contentTitle: 'Built for Scale',
      contentText: 'Robust infrastructure that grows with your business needs.',
    }
  }

  // Real Estate / Property
  if (r.includes('real estate') || r.includes('property') || r.includes('home') || r.includes('house') || r.includes('agent')) {
    return {
      type: 'realestate',
      title: 'Find Your Dream Home',
      subtitle: 'Premium properties in prime locations',
      features: [
        { icon: '🏠', title: 'Exclusive Listings', desc: 'Curated properties' },
        { icon: '🔑', title: 'Virtual Tours', desc: 'Explore from anywhere' },
        { icon: '📋', title: 'Expert Agents', desc: 'Trusted guidance' },
      ],
      ctaText: 'Browse Listings',
      colors: { primary: '#1c1917', secondary: '#059669', accent: '#34d399' },
      contentTitle: 'Luxury Living',
      contentText: 'Exceptional properties matched to your lifestyle and preferences.',
    }
  }

  // Default / General Business
  return {
    type: 'business',
    title: 'Welcome',
    subtitle: 'Professional services tailored for you',
    features: [
      { icon: '⭐', title: 'Quality', desc: 'Excellence guaranteed' },
      { icon: '🎯', title: 'Results', desc: 'Proven track record' },
      { icon: '🤝', title: 'Trust', desc: 'Client focused' },
    ],
    ctaText: 'Get Started',
    colors: { primary: '#1e293b', secondary: '#3b82f6', accent: '#60a5fa' },
    contentTitle: 'Why Choose Us',
    contentText: 'Dedicated to delivering exceptional results for every client.',
  }
}

const ProgressivePreview = ({ progress, phase, projectName, userRequest = '' }: ProgressivePreviewProps) => {
  const [showHeader, setShowHeader] = useState(false)
  const [showHero, setShowHero] = useState(false)
  const [showFeatures, setShowFeatures] = useState(false)
  const [showContent, setShowContent] = useState(false)
  const [showFooter, setShowFooter] = useState(false)
  const [colorPhase, setColorPhase] = useState(0)

  // Get contextual content based on user request
  const siteContent = useMemo(() => detectSiteType(userRequest || projectName || ''), [userRequest, projectName])

  // Progressive reveal based on build progress
  useEffect(() => {
    if (progress >= 10) setShowHeader(true)
    if (progress >= 25) setShowHero(true)
    if (progress >= 40) setShowFeatures(true)
    if (progress >= 55) setShowContent(true)
    if (progress >= 70) setShowFooter(true)
    
    if (progress >= 60) setColorPhase(1)
    if (progress >= 75) setColorPhase(2)
    if (progress >= 90) setColorPhase(3)
  }, [progress])

  const { colors } = siteContent
  
  const getBackground = () => {
    if (colorPhase >= 3) return `linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 100%)`
    if (colorPhase >= 2) return 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)'
    if (colorPhase >= 1) return '#f8fafc'
    return '#f1f5f9'
  }

  const getTextColor = () => colorPhase >= 3 ? '#ffffff' : colors.primary
  const getAccentColor = () => colorPhase >= 2 ? colors.secondary : '#cbd5e1'

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
          borderBottom: colorPhase >= 1 ? '1px solid rgba(0,0,0,0.08)' : 'none',
          opacity: showHeader ? 1 : 0,
          transform: showHeader ? 'translateY(0)' : 'translateY(-20px)',
          transition: 'all 0.6s ease-out',
          backgroundColor: colorPhase >= 2 ? 'rgba(255,255,255,0.95)' : 'transparent',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: '10px',
              background: colorPhase >= 2 ? `linear-gradient(135deg, ${colors.secondary}, ${colors.accent})` : getAccentColor(),
              transition: 'all 0.5s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 18,
            }}
          >
            {colorPhase >= 2 && siteContent.features[0].icon}
          </Box>
          <Typography
            sx={{
              fontWeight: 700,
              fontSize: 18,
              color: colorPhase >= 3 ? colors.primary : getTextColor(),
              opacity: colorPhase >= 1 ? 1 : 0.5,
              transition: 'all 0.5s ease',
            }}
          >
            {colorPhase >= 1 ? siteContent.title : 'Loading...'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 3 }}>
          {['Home', 'Services', 'About', 'Contact'].map((item, i) => (
            <Typography
              key={item}
              sx={{
                fontSize: 14,
                color: colorPhase >= 1 ? (colorPhase >= 3 ? colors.primary : '#64748b') : '#cbd5e1',
                fontWeight: 500,
                opacity: showHeader ? 1 : 0,
                transition: `all 0.4s ease ${i * 0.1}s`,
              }}
            >
              {colorPhase >= 1 ? item : '●●●●'}
            </Typography>
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
        <Box sx={{ mb: 3 }}>
          {colorPhase >= 1 ? (
            <Typography
              variant="h2"
              sx={{
                fontWeight: 800,
                fontSize: { xs: 40, md: 56 },
                color: getTextColor(),
                transition: 'color 0.5s ease',
                lineHeight: 1.1,
              }}
            >
              {siteContent.title.split(' ')[0]}
              <br />
              <span style={{ color: colorPhase >= 3 ? colors.accent : colors.secondary }}>
                {siteContent.title.split(' ').slice(1).join(' ') || 'Excellence'}
              </span>
            </Typography>
          ) : (
            <Box sx={{ width: '60%', height: 100, background: '#e2e8f0', borderRadius: 3, mx: 'auto' }} />
          )}
        </Box>

        <Box sx={{ mb: 4 }}>
          {colorPhase >= 1 ? (
            <Typography
              sx={{
                fontSize: 20,
                color: colorPhase >= 3 ? 'rgba(255,255,255,0.85)' : '#64748b',
                maxWidth: 500,
                mx: 'auto',
                lineHeight: 1.6,
              }}
            >
              {siteContent.subtitle}
            </Typography>
          ) : (
            <Box sx={{ width: '40%', height: 24, background: '#e2e8f0', borderRadius: 2, mx: 'auto' }} />
          )}
        </Box>

        <Box
          sx={{
            display: 'inline-block',
            px: 5,
            py: 2,
            borderRadius: '50px',
            background: colorPhase >= 2 
              ? `linear-gradient(135deg, ${colors.secondary} 0%, ${colors.accent} 100%)`
              : '#e2e8f0',
            boxShadow: colorPhase >= 2 
              ? `0 15px 40px ${colors.secondary}40`
              : 'none',
            transition: 'all 0.5s ease',
            cursor: 'pointer',
          }}
        >
          <Typography
            sx={{
              color: colorPhase >= 2 ? '#fff' : 'transparent',
              fontWeight: 700,
              fontSize: 17,
            }}
          >
            {siteContent.ctaText}
          </Typography>
        </Box>
      </Box>

      {/* Features Section */}
      <Box
        sx={{
          py: 8,
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
            gap: 4,
            maxWidth: 1000,
            mx: 'auto',
          }}
        >
          {siteContent.features.map((feature, i) => (
            <Box
              key={i}
              sx={{
                p: 4,
                borderRadius: 4,
                background: colorPhase >= 2 
                  ? 'rgba(255,255,255,0.15)'
                  : '#fff',
                backdropFilter: colorPhase >= 2 ? 'blur(20px)' : 'none',
                boxShadow: colorPhase >= 1 
                  ? '0 8px 32px rgba(0,0,0,0.08)'
                  : 'none',
                textAlign: 'center',
                opacity: showFeatures ? 1 : 0,
                transform: showFeatures ? 'translateY(0)' : 'translateY(20px)',
                transition: `all 0.6s ease ${i * 0.15}s`,
                border: colorPhase >= 2 ? '1px solid rgba(255,255,255,0.2)' : 'none',
              }}
            >
              <Box
                sx={{
                  width: 70,
                  height: 70,
                  borderRadius: '20px',
                  background: colorPhase >= 2 
                    ? `linear-gradient(135deg, ${colors.secondary}, ${colors.accent})`
                    : '#f1f5f9',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  mx: 'auto',
                  mb: 3,
                  fontSize: 32,
                  transition: 'all 0.5s ease',
                }}
              >
                {colorPhase >= 1 ? feature.icon : '○'}
              </Box>
              {colorPhase >= 1 ? (
                <>
                  <Typography sx={{ fontWeight: 700, mb: 1, fontSize: 18, color: getTextColor() }}>
                    {feature.title}
                  </Typography>
                  <Typography sx={{ fontSize: 15, color: colorPhase >= 3 ? 'rgba(255,255,255,0.75)' : '#64748b' }}>
                    {feature.desc}
                  </Typography>
                </>
              ) : (
                <>
                  <Box sx={{ width: '70%', height: 20, background: '#e2e8f0', borderRadius: 2, mx: 'auto', mb: 1 }} />
                  <Box sx={{ width: '90%', height: 14, background: '#e2e8f0', borderRadius: 2, mx: 'auto' }} />
                </>
              )}
            </Box>
          ))}
        </Box>
      </Box>

      {/* Content Section */}
      <Box
        sx={{
          py: 8,
          px: 4,
          opacity: showContent ? 1 : 0,
          transform: showContent ? 'translateY(0)' : 'translateY(40px)',
          transition: 'all 0.8s ease-out',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            gap: 6,
            maxWidth: 1000,
            mx: 'auto',
            alignItems: 'center',
          }}
        >
          <Box
            sx={{
              flex: 1,
              height: 300,
              borderRadius: 4,
              background: colorPhase >= 2
                ? `linear-gradient(135deg, ${colors.secondary}30, ${colors.accent}30)`
                : '#e2e8f0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.6s ease',
              border: colorPhase >= 2 ? `2px solid ${colors.accent}40` : 'none',
            }}
          >
            {colorPhase >= 2 && (
              <Typography sx={{ fontSize: 80 }}>{siteContent.features[1].icon}</Typography>
            )}
          </Box>
          
          <Box sx={{ flex: 1 }}>
            {colorPhase >= 1 ? (
              <>
                <Typography
                  variant="h4"
                  sx={{ fontWeight: 800, mb: 2, color: getTextColor(), fontSize: 32 }}
                >
                  {siteContent.contentTitle}
                </Typography>
                <Typography sx={{ 
                  color: colorPhase >= 3 ? 'rgba(255,255,255,0.8)' : '#64748b', 
                  lineHeight: 1.8,
                  fontSize: 17,
                  mb: 3,
                }}>
                  {siteContent.contentText}
                </Typography>
                {colorPhase >= 2 && (
                  <Box
                    sx={{
                      display: 'inline-block',
                      px: 3,
                      py: 1.5,
                      borderRadius: '30px',
                      border: `2px solid ${colorPhase >= 3 ? colors.accent : colors.secondary}`,
                      color: colorPhase >= 3 ? colors.accent : colors.secondary,
                      fontWeight: 600,
                      fontSize: 15,
                    }}
                  >
                    Learn More →
                  </Box>
                )}
              </>
            ) : (
              <>
                <Box sx={{ width: '80%', height: 32, background: '#e2e8f0', borderRadius: 2, mb: 3 }} />
                <Box sx={{ width: '100%', height: 16, background: '#e2e8f0', borderRadius: 2, mb: 1.5 }} />
                <Box sx={{ width: '95%', height: 16, background: '#e2e8f0', borderRadius: 2, mb: 1.5 }} />
                <Box sx={{ width: '70%', height: 16, background: '#e2e8f0', borderRadius: 2 }} />
              </>
            )}
          </Box>
        </Box>
      </Box>

      {/* Footer */}
      <Box
        sx={{
          py: 5,
          px: 4,
          mt: 6,
          borderTop: colorPhase >= 1 ? `1px solid ${colorPhase >= 3 ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)'}` : 'none',
          opacity: showFooter ? 1 : 0,
          transform: showFooter ? 'translateY(0)' : 'translateY(20px)',
          transition: 'all 0.6s ease-out',
          background: colorPhase >= 2 ? 'rgba(0,0,0,0.05)' : 'transparent',
        }}
      >
        <Box sx={{ textAlign: 'center' }}>
          <Typography sx={{ color: colorPhase >= 3 ? 'rgba(255,255,255,0.6)' : '#94a3b8', fontSize: 14 }}>
            {colorPhase >= 1 ? `© 2024 ${siteContent.title}. All rights reserved.` : '●●● ●●●● ●●●●●'}
          </Typography>
        </Box>
      </Box>

      {/* Floating Progress Indicator */}
      <Box
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          background: colorPhase >= 2 ? colors.primary : 'rgba(0,0,0,0.85)',
          color: '#fff',
          px: 4,
          py: 2,
          borderRadius: 50,
          fontSize: 14,
          fontWeight: 600,
          boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          transition: 'all 0.3s ease',
        }}
      >
        <Box
          sx={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: colors.accent,
            animation: 'pulse 1.5s ease-in-out infinite',
            '@keyframes pulse': {
              '0%, 100%': { opacity: 1, transform: 'scale(1)' },
              '50%': { opacity: 0.5, transform: 'scale(1.3)' },
            },
          }}
        />
        {progress}% — {phase}
      </Box>
    </Box>
  )
}

export default ProgressivePreview
