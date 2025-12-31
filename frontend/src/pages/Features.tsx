import { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Paper,
  Grid,
  Chip,
  Divider,
  Card,
  CardContent,
  LinearProgress,
  Alert,
  Button,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked'
import BuildIcon from '@mui/icons-material/Build'
import SpeedIcon from '@mui/icons-material/Speed'
import StorageIcon from '@mui/icons-material/Storage'
import SecurityIcon from '@mui/icons-material/Security'
import CodeIcon from '@mui/icons-material/Code'
import CloudIcon from '@mui/icons-material/Cloud'
import AnalyticsIcon from '@mui/icons-material/Analytics'
import ExtensionIcon from '@mui/icons-material/Extension'

interface Feature {
  name: string
  description: string
  status: 'implemented' | 'partial' | 'planned'
  category: string
  details?: string[]
}

const IMPLEMENTED_FEATURES: Feature[] = [
  {
    name: 'Component-Based Architecture',
    description: 'Projects decomposed into reusable building blocks',
    status: 'implemented',
    category: 'Core',
    details: [
      '48 building blocks in library',
      'Type/variant classification',
      'Semantic search for matching',
      'Automatic component decomposition',
    ],
  },
  {
    name: 'Library Reuse System',
    description: 'Intelligent reuse of existing components',
    status: 'implemented',
    category: 'Core',
    details: [
      '20% similarity threshold',
      'Usage tracking per component',
      'Cross-project reuse',
      'Component scoring system',
    ],
  },
  {
    name: 'Hybrid Deployment',
    description: 'Fast Vercel deploys with Render fallback',
    status: 'implemented',
    category: 'Deployment',
    details: [
      'Vercel: 30-60 second deploys',
      'Render: 5-10 min for backends',
      'Automatic provider selection',
      'SPA routing support',
    ],
  },
  {
    name: 'Real-Time Data Gateway',
    description: 'Unified API for external data services',
    status: 'implemented',
    category: 'Data',
    details: [
      'CoinGecko, CoinDesk integration',
      'Direct browser calls for free APIs',
      'Response caching',
      'Fallback mechanisms',
    ],
  },
  {
    name: 'Admin Panel with Builder',
    description: 'Built-in admin + chat-based editor for every app',
    status: 'implemented',
    category: 'Features',
    details: [
      'Builder: Chat interface + live preview',
      'Overview: Stats & quick actions',
      'Analytics: Views, sessions, API calls',
      'Settings: Refresh interval, password change',
    ],
  },
  {
    name: 'Code Validation & Sanitization',
    description: 'Pre-deployment code quality checks',
    status: 'implemented',
    category: 'Quality',
    details: [
      'Syntax validation',
      'Auto-fix for common issues',
      'JSX balance checking',
      'TypeScript to JS conversion',
    ],
  },
  {
    name: 'Connector System',
    description: 'Type-safe connections between components',
    status: 'implemented',
    category: 'Architecture',
    details: [
      'DATA_IN/OUT, EVENT, STATE types',
      'Automatic wire generation',
      'Connection validation',
      'Standard interface library',
    ],
  },
  {
    name: 'User Rules System',
    description: 'Persistent enforcement of owner rules',
    status: 'implemented',
    category: 'Governance',
    details: [
      'No emoji enforcement',
      'Rule violation detection',
      'Automatic code cleanup',
      'Problem registry',
    ],
  },
  {
    name: 'AI-Powered Generation',
    description: 'Claude Opus 4.5 for intelligent code generation',
    status: 'implemented',
    category: 'AI',
    details: [
      'Prompt decomposition',
      'Context-aware composition',
      'Industry templates',
      'Component adaptation',
    ],
  },
  {
    name: 'Functional Settings View',
    description: 'Settings that actually work in generated apps',
    status: 'implemented',
    category: 'Features',
    details: [
      'localStorage persistence',
      'Dynamic refresh intervals',
      'Real connection status',
      'Cache management',
    ],
  },
]

const PLANNED_FEATURES: Feature[] = [
  {
    name: 'Design Editor',
    description: 'Live visual CSS editing',
    status: 'planned',
    category: 'Design',
    details: [
      'Design token system planned',
      'Live preview pending',
      'Style persistence pending',
    ],
  },
  {
    name: 'Self-Improvement System',
    description: 'Automatic library healing and upgrades',
    status: 'planned',
    category: 'AI',
    details: [
      'Feedback collection planned',
      'Test registry planned',
      'Automatic engine upgrades planned',
      'Metric-based improvements planned',
    ],
  },
]

// Move completed features from "partial" to implemented
const RECENTLY_COMPLETED: Feature[] = [
  {
    name: 'Supabase Database Integration',
    description: 'Auto-provision databases for customer apps',
    status: 'implemented',
    category: 'Database',
    details: [
      'Backend models and API',
      'Frontend Settings UI',
      'Auto-provisioning button',
      'Table viewer',
    ],
  },
  {
    name: 'User Authentication',
    description: 'Magic link and OAuth login for apps',
    status: 'implemented',
    category: 'Auth',
    details: [
      'Supabase Auth configured',
      'Settings UI with toggles',
      'OAuth credentials input',
      'Email/password & magic link',
    ],
  },
  {
    name: 'Custom Domains',
    description: 'Connect custom domains to deployed apps',
    status: 'implemented',
    category: 'Deployment',
    details: [
      'Vercel API integration',
      'DNS verification UI',
      'Domain management panel',
      'SSL auto-provisioning',
    ],
  },
  {
    name: 'Payment Integration (Stripe)',
    description: 'Accept payments in generated apps',
    status: 'implemented',
    category: 'Payments',
    details: [
      'Stripe service created',
      'Connect button in settings',
      'Product management',
      'Status indicator',
    ],
  },
  {
    name: 'Analytics Dashboard',
    description: 'Track app usage and performance',
    status: 'implemented',
    category: 'Analytics',
    details: [
      'Tracking service',
      'Dashboard with charts',
      'Time range selector',
      'Top pages view',
    ],
  },
  {
    name: 'Version Control & Rollback',
    description: 'Code snapshots with 1-click rollback',
    status: 'implemented',
    category: 'DevOps',
    details: [
      'Version history list',
      'Diff view with syntax highlighting',
      'Rollback confirmation dialog',
      'Auto-snapshot on deploy',
    ],
  },
  {
    name: 'SEO Optimization',
    description: 'Meta tags, sitemap, structured data',
    status: 'implemented',
    category: 'SEO',
    details: [
      'SEO service',
      'Meta tag generation',
      'Sitemap generation',
      'Open Graph tags',
    ],
  },
  {
    name: 'File Storage',
    description: 'Upload and manage files in apps',
    status: 'implemented',
    category: 'Storage',
    details: [
      'Supabase Storage',
      'Bucket viewer',
      'Settings integration',
    ],
  },
]

const categoryIcons: Record<string, React.ReactNode> = {
  Core: <BuildIcon />,
  Deployment: <CloudIcon />,
  Data: <StorageIcon />,
  Features: <ExtensionIcon />,
  Quality: <CodeIcon />,
  Architecture: <ExtensionIcon />,
  Governance: <SecurityIcon />,
  AI: <SpeedIcon />,
  Database: <StorageIcon />,
  Auth: <SecurityIcon />,
  Payments: <AnalyticsIcon />,
  Analytics: <AnalyticsIcon />,
  DevOps: <CloudIcon />,
  Design: <BuildIcon />,
  SEO: <CodeIcon />,
  Storage: <StorageIcon />,
}

export default function Features() {
  const allImplemented = [...IMPLEMENTED_FEATURES, ...RECENTLY_COMPLETED]
  const implementedCount = allImplemented.length
  const plannedCount = PLANNED_FEATURES.length
  const totalFeatures = implementedCount + plannedCount
  const progressPercent = (implementedCount / totalFeatures) * 100

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" fontWeight="bold" gutterBottom>
          Faibric Features
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Complete list of implemented and planned features
        </Typography>

        {/* Progress Overview */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <Chip
                  icon={<CheckCircleIcon />}
                  label={`${implementedCount} Implemented`}
                  color="success"
                />
                <Chip
                  icon={<RadioButtonUncheckedIcon />}
                  label={`${plannedCount} Planned`}
                  color="default"
                />
              </Box>
              <LinearProgress
                variant="determinate"
                value={progressPercent}
                sx={{ height: 10, borderRadius: 5 }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                {progressPercent.toFixed(0)}% feature completion
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <Alert severity="info">
                <strong>Library Stats:</strong> 48 building blocks, 12 component types
              </Alert>
            </Grid>
          </Grid>
        </Paper>
      </Box>

      {/* Implemented Features */}
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 3, color: 'success.main' }}>
        Implemented Features ({allImplemented.length})
      </Typography>
      <Grid container spacing={3} sx={{ mb: 6 }}>
        {allImplemented.map((feature, index) => (
          <Grid item xs={12} md={6} key={index}>
            <Card sx={{ height: '100%', borderLeft: 4, borderColor: 'success.main' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  {categoryIcons[feature.category] || <BuildIcon />}
                  <Chip label={feature.category} size="small" variant="outlined" />
                  <CheckCircleIcon color="success" sx={{ ml: 'auto' }} />
                </Box>
                <Typography variant="h6" fontWeight="bold">
                  {feature.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {feature.description}
                </Typography>
                {feature.details && (
                  <Box component="ul" sx={{ m: 0, pl: 2 }}>
                    {feature.details.map((detail, i) => (
                      <Typography component="li" variant="body2" key={i}>
                        {detail}
                      </Typography>
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Divider sx={{ my: 4 }} />

      {/* Planned/Partial Features */}
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 3, color: 'warning.main' }}>
        In Progress / Planned Features
      </Typography>
      <Grid container spacing={3}>
        {PLANNED_FEATURES.map((feature, index) => (
          <Grid item xs={12} md={6} key={index}>
            <Card
              sx={{
                height: '100%',
                borderLeft: 4,
                borderColor: feature.status === 'partial' ? 'warning.main' : 'grey.400',
                opacity: feature.status === 'planned' ? 0.8 : 1,
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  {categoryIcons[feature.category] || <BuildIcon />}
                  <Chip label={feature.category} size="small" variant="outlined" />
                  <Chip
                    label={feature.status === 'partial' ? 'In Progress' : 'Planned'}
                    size="small"
                    color={feature.status === 'partial' ? 'warning' : 'default'}
                    sx={{ ml: 'auto' }}
                  />
                </Box>
                <Typography variant="h6" fontWeight="bold">
                  {feature.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {feature.description}
                </Typography>
                {feature.details && (
                  <Box component="ul" sx={{ m: 0, pl: 2 }}>
                    {feature.details.map((detail, i) => (
                      <Typography component="li" variant="body2" key={i}>
                        {detail}
                      </Typography>
                    ))}
                  </Box>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Test Section */}
      <Paper sx={{ p: 4, mt: 6, bgcolor: 'grey.50' }}>
        <Typography variant="h5" fontWeight="bold" gutterBottom>
          Feature Testing
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          All implemented features are tested by building real projects and verifying:
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Alert severity="success" sx={{ height: '100%' }}>
              <strong>Component Reuse</strong>
              <br />
              100% reuse rate in test builds
            </Alert>
          </Grid>
          <Grid item xs={12} md={4}>
            <Alert severity="success" sx={{ height: '100%' }}>
              <strong>Deployment Speed</strong>
              <br />
              ~2-3 min from prompt to live URL
            </Alert>
          </Grid>
          <Grid item xs={12} md={4}>
            <Alert severity="success" sx={{ height: '100%' }}>
              <strong>Admin Panel</strong>
              <br />
              /faibric route works on all apps
            </Alert>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  )
}

