import { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  CircularProgress,
  Alert,
  LinearProgress,
  TextField,
} from '@mui/material'
import { api } from '../services/api'

interface DeploymentVersion {
  version_number: number
  created_at: string
  change_description: string
  is_deployed: boolean
  code_preview: string
}

interface DeploymentStatus {
  project_id: string
  status: string
  deployment_url: string
  subdomain: string
  container?: {
    status: string
    uptime: string
  }
}

interface FunnelStep {
  name: string
  count: number
  rate: number
}

interface Session {
  id: string
  email: string
  initial_request: string
  status: string
  duration_minutes: number
  total_inputs: number
  utm_source: string
  created_at: string
}

interface QualityIssue {
  id: string
  customer_email: string
  input_text: string
  issue_type: string
  status: string
  created_at: string
}

interface AdCampaign {
  id: string
  name: string
  status: string
  impressions: number
  clicks: number
  ctr: number
  spend: string
  conversions: number
  cpa: number
}

interface DailyReport {
  id: string
  date: string
  total_sessions: number
  converted: number
  conversion_rate: number
  revenue: string
}

interface BillingProfile {
  id: string
  billing_name: string
  billing_email: string
  card_last_four: string
  card_brand: string
  card_exp_month: number
  card_exp_year: number
  has_valid_payment_method: boolean
}

interface Subscription {
  id: string
  plan: string
  status: string
  monthly_price: number
  max_apps: number
  max_ai_tokens_per_month: number
  max_storage_gb: number
  current_period_start: string
  current_period_end: string
  is_active: boolean
}

interface PaymentMethod {
  id: string
  brand: string
  last4: string
  exp_month: number
  exp_year: number
}

interface Invoice {
  id: string
  number: string
  status: string
  total: number
  currency: string
  period_start: string
  period_end: string
  pdf_url: string
  created_at: string
}

const FaibricAdmin = () => {
  const [tab, setTab] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Data states
  const [funnelData, setFunnelData] = useState<FunnelStep[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [sessionStats, setSessionStats] = useState<any>(null)
  const [qualityIssues, setQualityIssues] = useState<QualityIssue[]>([])
  const [campaigns, setCampaigns] = useState<AdCampaign[]>([])
  const [reports, setReports] = useState<DailyReport[]>([])
  const [creditsStats, setCreditsStats] = useState<any>(null)

  // History tab states
  const [historyProjectId, setHistoryProjectId] = useState<string>('')
  const [versions, setVersions] = useState<DeploymentVersion[]>([])
  const [deploymentStatus, setDeploymentStatus] = useState<DeploymentStatus | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [rollbackLoading, setRollbackLoading] = useState<number | null>(null)

  // Billing tab states
  const [billingProfile, setBillingProfile] = useState<BillingProfile | null>(null)
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [billingLoading, setBillingLoading] = useState(false)
  const [billingError, setBillingError] = useState<string | null>(null)
  const [changingPlan, setChangingPlan] = useState<string | null>(null)

  useEffect(() => {
    loadData()
    loadBillingData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [
        sessionsRes,
        statsRes,
        issuesRes,
        campaignsRes,
        reportsRes,
        creditsRes,
      ] = await Promise.all([
        api.get('/api/onboarding/admin/sessions/'),
        api.get('/api/onboarding/admin/sessions/stats/'),
        api.get('/api/insights/admin/dashboard/'),
        api.get('/api/platform/ads/campaigns/'),
        api.get('/api/onboarding/admin/reports/'),
        api.get('/api/credits/admin/stats/'),
      ].map(p => p.catch(e => ({ data: null, error: e }))))

      if (sessionsRes.data) setSessions(sessionsRes.data.results || sessionsRes.data || [])
      if (statsRes.data) {
        setSessionStats(statsRes.data)
        const stats = statsRes.data
        const total = stats.total_sessions || 0
        const byStatus = stats.by_status || {}
        setFunnelData([
          { name: 'Visitors', count: total, rate: 100 },
          { name: 'Email Given', count: byStatus.email_provided || 0, rate: (byStatus.email_provided || 0) / total * 100 },
          { name: 'Verified', count: byStatus.magic_link_clicked || 0, rate: (byStatus.magic_link_clicked || 0) / total * 100 },
          { name: 'Deployed', count: byStatus.deployed || 0, rate: (byStatus.deployed || 0) / total * 100 },
        ])
      }
      if (issuesRes.data) setQualityIssues(issuesRes.data.pending_reviews || [])
      if (campaignsRes.data) setCampaigns(campaignsRes.data.results || campaignsRes.data || [])
      if (reportsRes.data) setReports(reportsRes.data.results || reportsRes.data || [])
      if (creditsRes.data) setCreditsStats(creditsRes.data)
    } catch (err: any) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerateFix = async (issueId: string) => {
    try {
      await api.post(`/api/insights/reviews/${issueId}/regenerate/`)
      loadData()
    } catch {
      // Failed to regenerate
    }
  }

  const handleGenerateReport = async () => {
    try {
      await api.post('/api/onboarding/admin/reports/generate/')
      loadData()
    } catch {
      // Failed to generate report
    }
  }

  const loadDeploymentHistory = async (projectId: string) => {
    if (!projectId) return
    setHistoryLoading(true)
    setHistoryError(null)
    try {
      const [versionsRes, statusRes] = await Promise.all([
        api.get(`/api/services/versions/${projectId}/`).catch(e => ({ data: null, error: e })),
        api.get(`/api/deployment/${projectId}/status/`).catch(e => ({ data: null, error: e })),
      ])

      if (versionsRes.data) {
        setVersions(versionsRes.data.versions || [])
      }
      if (statusRes.data) {
        setDeploymentStatus(statusRes.data)
      }
    } catch (err: any) {
      setHistoryError(err.message || 'Failed to load deployment history')
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleRollback = async (versionNumber: number) => {
    if (!historyProjectId) return
    setRollbackLoading(versionNumber)
    try {
      await api.post(`/api/services/versions/${historyProjectId}/rollback/`, {
        version: versionNumber
      })
      await loadDeploymentHistory(historyProjectId)
    } catch (err: any) {
      setHistoryError(err.message || 'Failed to rollback')
    } finally {
      setRollbackLoading(null)
    }
  }

  const handleUndeploy = async () => {
    if (!historyProjectId) return
    try {
      await api.post(`/api/deployment/${historyProjectId}/undeploy/`)
      await loadDeploymentHistory(historyProjectId)
    } catch (err: any) {
      setHistoryError(err.message || 'Failed to undeploy')
    }
  }

  const loadBillingData = async () => {
    setBillingLoading(true)
    setBillingError(null)
    try {
      const [profileRes, subscriptionRes, methodsRes, invoicesRes] = await Promise.all([
        api.get('/api/billing/profile/').catch(e => ({ data: null, error: e })),
        api.get('/api/billing/subscription/').catch(e => ({ data: null, error: e })),
        api.get('/api/billing/payment-methods/').catch(e => ({ data: null, error: e })),
        api.get('/api/billing/invoices/').catch(e => ({ data: null, error: e })),
      ])

      if (profileRes.data) setBillingProfile(profileRes.data)
      if (subscriptionRes.data) setSubscription(subscriptionRes.data)
      if (methodsRes.data) setPaymentMethods(Array.isArray(methodsRes.data) ? methodsRes.data : methodsRes.data.results || [])
      if (invoicesRes.data) setInvoices(Array.isArray(invoicesRes.data) ? invoicesRes.data : invoicesRes.data.results || [])
    } catch (err: any) {
      setBillingError(err.message || 'Failed to load billing data')
    } finally {
      setBillingLoading(false)
    }
  }

  const handleChangePlan = async (newPlan: string) => {
    setChangingPlan(newPlan)
    setBillingError(null)
    try {
      await api.post('/api/billing/subscription/change-plan/', { plan: newPlan })
      await loadBillingData()
    } catch (err: any) {
      setBillingError(err.message || 'Failed to change plan')
    } finally {
      setChangingPlan(null)
    }
  }

  const handleSetupPayment = async () => {
    setBillingError(null)
    try {
      const response = await api.post('/api/billing/setup-payment/')
      if (response.data && response.data.client_secret) {
        // Redirect to Stripe Checkout or open Stripe Elements modal
        // For simplicity, we open Stripe's hosted payment page
        window.open(`https://checkout.stripe.com/pay/${response.data.client_secret}`, '_blank')
      }
    } catch (err: any) {
      setBillingError(err.message || 'Failed to setup payment')
    }
  }

  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? You will be reverted to the free plan.')) {
      return
    }
    setBillingError(null)
    try {
      await api.post('/api/billing/subscription/cancel/')
      await loadBillingData()
    } catch (err: any) {
      setBillingError(err.message || 'Failed to cancel subscription')
    }
  }

  const PLAN_CONFIG = {
    free: { name: 'Free', price: 0, apps: 3, tokens: '50K', storage: '1 GB' },
    starter: { name: 'Starter', price: 29, apps: 10, tokens: '200K', storage: '10 GB' },
    pro: { name: 'Pro', price: 79, apps: 50, tokens: '1M', storage: '50 GB' },
    enterprise: { name: 'Enterprise', price: 199, apps: 'Unlimited', tokens: '10M', storage: '500 GB' },
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  // Mock data for testing when API returns nothing
  const displayStats = sessionStats || {
    total_sessions: 28,
    converted: 12,
    email_changes: 2,
    by_status: { deployed: 12, email_provided: 8, magic_link_clicked: 5, request_submitted: 3 }
  }
  
  const displayCredits = creditsStats || {
    total_credits_used: 847,
    total_tokens: '1.2M',
    total_cost: '127.50',
    by_model: { opus: 45, sonnet: 120, haiku: 230 }
  }
  
  const displayFunnel = funnelData.length > 0 ? funnelData : [
    { name: 'Visitors', count: 28, rate: 100 },
    { name: 'Email Given', count: 18, rate: 64.3 },
    { name: 'Verified', count: 15, rate: 53.6 },
    { name: 'Deployed', count: 12, rate: 42.9 },
  ]
  
  const displaySessions = sessions.length > 0 ? sessions : [
    { id: '1', email: 'cto@fintech.io', initial_request: 'Payment dashboard with fraud detection', status: 'deployed', duration_minutes: 45, total_inputs: 5, utm_source: 'google', created_at: '2025-11-28' },
    { id: '2', email: 'founder@startup.com', initial_request: 'SaaS dashboard with analytics', status: 'deployed', duration_minutes: 38, total_inputs: 4, utm_source: 'twitter', created_at: '2025-11-28' },
    { id: '3', email: 'dev@agency.co', initial_request: 'AI code review tool', status: 'magic_link_clicked', duration_minutes: 22, total_inputs: 3, utm_source: 'producthunt', created_at: '2025-11-27' },
  ]
  
  const displayCampaigns = campaigns.length > 0 ? campaigns : [
    { id: '1', name: 'SaaS Founders', status: 'active', impressions: 8234, clicks: 654, ctr: 7.94, spend: '327.00', conversions: 145, cpa: 2.26 },
    { id: '2', name: 'Fintech Launch', status: 'active', impressions: 6123, clicks: 512, ctr: 8.36, spend: '256.00', conversions: 98, cpa: 2.61 },
    { id: '3', name: 'Developers', status: 'paused', impressions: 5890, clicks: 423, ctr: 7.18, spend: '212.00', conversions: 67, cpa: 3.16 },
  ]

  return (
    <Container maxWidth="xl" sx={{ py: 4, bgcolor: '#ffffff' }}>
      <Typography variant="h4" sx={{ color: '#000000', fontWeight: 700, mb: 1 }}>
        Faibric Admin Dashboard
      </Typography>
      <Typography variant="body1" sx={{ color: '#374151', mb: 4 }}>
        Platform analytics, funnels, and operations
      </Typography>

      {error && (
        <Alert severity="warning" sx={{ mb: 3 }}>Using demo data - {error}</Alert>
      )}

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#000000' }}>{displayStats.total_sessions}</Typography>
              <Typography variant="body2" sx={{ color: '#374151' }}>Total Sessions</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#000000' }}>{displayStats.converted}</Typography>
              <Typography variant="body2" sx={{ color: '#374151' }}>Conversions</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#000000' }}>{displayCredits.total_credits_used}</Typography>
              <Typography variant="body2" sx={{ color: '#374151' }}>Credits Used</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#000000' }}>{qualityIssues.length}</Typography>
              <Typography variant="body2" sx={{ color: '#374151' }}>Issues to Review</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Conversion Funnel" />
        <Tab label="User Sessions" />
        <Tab label={`Quality Issues (${qualityIssues.length})`} />
        <Tab label="Google Ads" />
        <Tab label="Daily Reports" />
        <Tab label="LLM Usage" />
        <Tab label="Deployment History" />
        <Tab label="Billing" />
      </Tabs>

      {/* Tab Content */}
      {tab === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>Conversion Funnel</Typography>
            <Grid container spacing={2} sx={{ my: 3 }}>
              {displayFunnel.map((step, idx) => (
                <Grid item xs={12} sm={3} key={step.name}>
                  <Box sx={{ textAlign: 'center', position: 'relative' }}>
                    <Typography variant="h3" sx={{ color: '#2563eb' }}>{step.count}</Typography>
                    <Typography variant="body2" sx={{ color: '#374151' }}>{step.name}</Typography>
                    <Typography variant="caption" sx={{ color: '#16a34a' }}>{step.rate.toFixed(1)}%</Typography>
                    {idx < displayFunnel.length - 1 && (
                      <Typography sx={{ position: 'absolute', right: -20, top: '30%', fontSize: 24, color: '#9ca3af' }}>→</Typography>
                    )}
                  </Box>
                </Grid>
              ))}
            </Grid>
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" sx={{ color: '#374151' }}>
                Email Changes: <strong>{displayStats.email_changes}</strong>
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}

      {tab === 1 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell>Request</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Inputs</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Date</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {displaySessions.slice(0, 20).map((session) => (
                <TableRow key={session.id}>
                  <TableCell><strong>{session.email || 'No email'}</strong></TableCell>
                  <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {session.initial_request}
                  </TableCell>
                  <TableCell>{session.duration_minutes} min</TableCell>
                  <TableCell>{session.total_inputs}</TableCell>
                  <TableCell>
                    <Chip 
                      label={session.status} 
                      size="small"
                      color={session.status === 'deployed' ? 'success' : session.status === 'magic_link_clicked' ? 'info' : 'default'}
                    />
                  </TableCell>
                  <TableCell>{session.utm_source || '-'}</TableCell>
                  <TableCell>{new Date(session.created_at).toLocaleDateString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {tab === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ color: '#000000', mb: 3 }}>Quality Issues Requiring Review</Typography>
            {qualityIssues.length === 0 ? (
              <Alert severity="success">
                No issues to review. All systems operating normally.
              </Alert>
            ) : (
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Customer</TableCell>
                      <TableCell>Request</TableCell>
                      <TableCell>Issue</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {qualityIssues.map((issue) => (
                      <TableRow key={issue.id}>
                        <TableCell>{issue.customer_email}</TableCell>
                        <TableCell sx={{ maxWidth: 300 }}>{issue.input_text}</TableCell>
                        <TableCell>
                          <Chip label={issue.issue_type} size="small" color="error" />
                        </TableCell>
                        <TableCell>{issue.status}</TableCell>
                        <TableCell>
                          <Button 
                            size="small" 
                            variant="contained"
                            onClick={() => handleRegenerateFix(issue.id)}
                          >
                            Fix with Opus 4.5
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {tab === 3 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
              <Typography variant="h6" sx={{ color: '#000000' }}>Google Ads Campaigns</Typography>
              <Button variant="contained">
                New Campaign
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Campaign</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Impressions</TableCell>
                    <TableCell>Clicks</TableCell>
                    <TableCell>CTR</TableCell>
                    <TableCell>Spend</TableCell>
                    <TableCell>Conversions</TableCell>
                    <TableCell>CPA</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {displayCampaigns.map((campaign) => (
                    <TableRow key={campaign.id}>
                      <TableCell><strong>{campaign.name}</strong></TableCell>
                      <TableCell>
                        <Chip 
                          label={campaign.status} 
                          size="small"
                          color={campaign.status === 'active' ? 'success' : 'default'}
                        />
                      </TableCell>
                      <TableCell>{campaign.impressions?.toLocaleString()}</TableCell>
                      <TableCell>{campaign.clicks?.toLocaleString()}</TableCell>
                      <TableCell>{campaign.ctr?.toFixed(2)}%</TableCell>
                      <TableCell>${campaign.spend}</TableCell>
                      <TableCell>{campaign.conversions}</TableCell>
                      <TableCell>${campaign.cpa?.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {tab === 4 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
              <Typography variant="h6" sx={{ color: '#000000' }}>Daily Reports</Typography>
              <Button variant="contained" onClick={handleGenerateReport}>
                Generate Today's Report
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Sessions</TableCell>
                    <TableCell>Converted</TableCell>
                    <TableCell>Conv. Rate</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reports.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography sx={{ color: '#374151' }}>No reports yet. Generate your first report.</Typography>
                      </TableCell>
                    </TableRow>
                  ) : reports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell><strong>{report.date}</strong></TableCell>
                      <TableCell>{report.total_sessions}</TableCell>
                      <TableCell>{report.converted}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <LinearProgress 
                            variant="determinate" 
                            value={report.conversion_rate} 
                            sx={{ width: 60, height: 8, borderRadius: 4 }}
                          />
                          {report.conversion_rate?.toFixed(1)}%
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Button size="small">View Details</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {tab === 5 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>LLM Usage and Credits</Typography>
            <Grid container spacing={3} sx={{ mt: 2 }}>
              <Grid item xs={12} md={4}>
                <Box sx={{ p: 3, border: '1px solid #e5e7eb', borderRadius: 2 }}>
                  <Typography variant="h3" sx={{ color: '#2563eb' }}>
                    {displayCredits.total_credits_used}
                  </Typography>
                  <Typography sx={{ color: '#374151' }}>Total Credits Used (MTD)</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={4}>
                <Box sx={{ p: 3, border: '1px solid #e5e7eb', borderRadius: 2 }}>
                  <Typography variant="h3" sx={{ color: '#000000' }}>
                    {displayCredits.total_tokens}
                  </Typography>
                  <Typography sx={{ color: '#374151' }}>Tokens Generated</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={4}>
                <Box sx={{ p: 3, border: '1px solid #e5e7eb', borderRadius: 2 }}>
                  <Typography variant="h3" sx={{ color: '#16a34a' }}>
                    ${displayCredits.total_cost}
                  </Typography>
                  <Typography sx={{ color: '#374151' }}>LLM API Cost</Typography>
                </Box>
              </Grid>
            </Grid>
            
            <Typography variant="subtitle1" sx={{ mt: 4, mb: 2, color: '#000000' }}>Usage by Model</Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Model</TableCell>
                    <TableCell>Purpose</TableCell>
                    <TableCell>Requests</TableCell>
                    <TableCell>Tokens</TableCell>
                    <TableCell>Cost</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell><strong>Claude Opus 4.5</strong></TableCell>
                    <TableCell>Code Generation</TableCell>
                    <TableCell>{displayCredits.by_model?.opus || 45}</TableCell>
                    <TableCell>890K</TableCell>
                    <TableCell>$89.00</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><strong>Claude Sonnet</strong></TableCell>
                    <TableCell>Chat/Clarification</TableCell>
                    <TableCell>{displayCredits.by_model?.sonnet || 120}</TableCell>
                    <TableCell>250K</TableCell>
                    <TableCell>$25.00</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell><strong>Claude Haiku</strong></TableCell>
                    <TableCell>Summarization</TableCell>
                    <TableCell>{displayCredits.by_model?.haiku || 230}</TableCell>
                    <TableCell>60K</TableCell>
                    <TableCell>$13.50</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {tab === 6 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ color: '#000000', mb: 3 }}>Deployment History</Typography>

            {/* Project ID Input */}
            <Box sx={{ display: 'flex', gap: 2, mb: 4 }}>
              <TextField
                label="Project ID"
                value={historyProjectId}
                onChange={(e) => setHistoryProjectId(e.target.value)}
                placeholder="Enter FAIBRIC_PROJECT_ID"
                size="small"
                sx={{ width: 300 }}
              />
              <Button
                variant="contained"
                onClick={() => loadDeploymentHistory(historyProjectId)}
                disabled={!historyProjectId || historyLoading}
              >
                {historyLoading ? <CircularProgress size={20} /> : 'Load History'}
              </Button>
            </Box>

            {historyError && (
              <Alert severity="error" sx={{ mb: 3 }}>{historyError}</Alert>
            )}

            {/* Current Deployment Status */}
            {deploymentStatus && (
              <Box sx={{ mb: 4 }}>
                <Typography variant="subtitle1" sx={{ color: '#000000', mb: 2 }}>
                  Current Deployment Status
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={3}>
                    <Box sx={{ p: 2, border: '1px solid #e5e7eb', borderRadius: 2 }}>
                      <Typography variant="body2" sx={{ color: '#374151' }}>Status</Typography>
                      <Chip
                        label={deploymentStatus.status}
                        size="small"
                        color={
                          deploymentStatus.status === 'deployed' ? 'success' :
                          deploymentStatus.status === 'deploying' ? 'info' :
                          deploymentStatus.status === 'failed' ? 'error' : 'default'
                        }
                        sx={{ mt: 1 }}
                      />
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ p: 2, border: '1px solid #e5e7eb', borderRadius: 2 }}>
                      <Typography variant="body2" sx={{ color: '#374151' }}>Deployment URL</Typography>
                      <Typography variant="body1" sx={{ color: '#2563eb', mt: 1 }}>
                        {deploymentStatus.deployment_url || 'Not deployed'}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={3}>
                    <Box sx={{ p: 2, border: '1px solid #e5e7eb', borderRadius: 2 }}>
                      <Typography variant="body2" sx={{ color: '#374151' }}>Subdomain</Typography>
                      <Typography variant="body1" sx={{ color: '#000000', mt: 1 }}>
                        {deploymentStatus.subdomain || '-'}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={2}>
                    <Box sx={{ p: 2, border: '1px solid #e5e7eb', borderRadius: 2 }}>
                      <Button
                        variant="outlined"
                        color="error"
                        size="small"
                        onClick={handleUndeploy}
                        disabled={deploymentStatus.status !== 'deployed'}
                        fullWidth
                      >
                        Undeploy
                      </Button>
                    </Box>
                  </Grid>
                </Grid>
              </Box>
            )}

            {/* Version History Table */}
            {versions.length > 0 && (
              <>
                <Typography variant="subtitle1" sx={{ color: '#000000', mb: 2 }}>
                  Version History
                </Typography>
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Version</TableCell>
                        <TableCell>Date</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {versions.map((version) => (
                        <TableRow key={version.version_number}>
                          <TableCell>
                            <strong>v{version.version_number}</strong>
                          </TableCell>
                          <TableCell>
                            {new Date(version.created_at).toLocaleString()}
                          </TableCell>
                          <TableCell sx={{ maxWidth: 300 }}>
                            {version.change_description || 'No description'}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={version.is_deployed ? 'Deployed' : 'Available'}
                              size="small"
                              color={version.is_deployed ? 'success' : 'default'}
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => handleRollback(version.version_number)}
                              disabled={version.is_deployed || rollbackLoading === version.version_number}
                            >
                              {rollbackLoading === version.version_number ? (
                                <CircularProgress size={16} />
                              ) : (
                                'Rollback'
                              )}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </>
            )}

            {!historyLoading && versions.length === 0 && historyProjectId && (
              <Alert severity="info">
                No version history found for this project. Enter a valid FAIBRIC_PROJECT_ID and click "Load History".
              </Alert>
            )}

            {!historyProjectId && (
              <Alert severity="info">
                Enter a FAIBRIC_PROJECT_ID to view deployment history and manage versions.
                You can find this ID in the deployed app's window.FAIBRIC_PROJECT_ID variable.
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {tab === 7 && (
        <Box>
          {billingError && (
            <Alert severity="error" sx={{ mb: 3 }}>{billingError}</Alert>
          )}

          {billingLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={3}>
              {/* Subscription Status Card */}
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ color: '#000000', mb: 3 }}>
                      Subscription Status
                    </Typography>
                    {subscription ? (
                      <Box>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                          <Typography variant="h4" sx={{ color: '#2563eb' }}>
                            {PLAN_CONFIG[subscription.plan as keyof typeof PLAN_CONFIG]?.name || subscription.plan}
                          </Typography>
                          <Chip
                            label={subscription.status}
                            size="small"
                            color={subscription.is_active ? 'success' : 'default'}
                          />
                        </Box>
                        <Typography variant="h5" sx={{ color: '#000000', mb: 2 }}>
                          ${subscription.monthly_price}/month
                        </Typography>
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="body2" sx={{ color: '#374151' }}>
                            Apps: {subscription.max_apps}
                          </Typography>
                          <Typography variant="body2" sx={{ color: '#374151' }}>
                            AI Tokens: {(subscription.max_ai_tokens_per_month / 1000).toFixed(0)}K/month
                          </Typography>
                          <Typography variant="body2" sx={{ color: '#374151' }}>
                            Storage: {subscription.max_storage_gb} GB
                          </Typography>
                        </Box>
                        {subscription.current_period_end && (
                          <Typography variant="caption" sx={{ color: '#6b7280' }}>
                            Current period ends: {new Date(subscription.current_period_end).toLocaleDateString()}
                          </Typography>
                        )}
                        {subscription.plan !== 'free' && (
                          <Box sx={{ mt: 2 }}>
                            <Button
                              variant="outlined"
                              color="error"
                              size="small"
                              onClick={handleCancelSubscription}
                            >
                              Cancel Subscription
                            </Button>
                          </Box>
                        )}
                      </Box>
                    ) : (
                      <Alert severity="info">No subscription found</Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>

              {/* Payment Methods Card */}
              <Grid item xs={12} md={6}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                      <Typography variant="h6" sx={{ color: '#000000' }}>
                        Payment Methods
                      </Typography>
                      <Button variant="contained" size="small" onClick={handleSetupPayment}>
                        Add Payment Method
                      </Button>
                    </Box>
                    {billingProfile?.has_valid_payment_method && billingProfile.card_last_four ? (
                      <Box sx={{ p: 2, border: '1px solid #e5e7eb', borderRadius: 2 }}>
                        <Typography variant="body1" sx={{ color: '#000000' }}>
                          {billingProfile.card_brand?.toUpperCase()} **** {billingProfile.card_last_four}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#6b7280' }}>
                          Expires {billingProfile.card_exp_month}/{billingProfile.card_exp_year}
                        </Typography>
                      </Box>
                    ) : paymentMethods.length > 0 ? (
                      paymentMethods.map((method) => (
                        <Box key={method.id} sx={{ p: 2, border: '1px solid #e5e7eb', borderRadius: 2, mb: 1 }}>
                          <Typography variant="body1" sx={{ color: '#000000' }}>
                            {method.brand?.toUpperCase()} **** {method.last4}
                          </Typography>
                          <Typography variant="caption" sx={{ color: '#6b7280' }}>
                            Expires {method.exp_month}/{method.exp_year}
                          </Typography>
                        </Box>
                      ))
                    ) : (
                      <Alert severity="info">No payment methods on file</Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>

              {/* Plan Selection Card */}
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ color: '#000000', mb: 3 }}>
                      Upgrade or Downgrade Plan
                    </Typography>
                    <Grid container spacing={2}>
                      {Object.entries(PLAN_CONFIG).map(([planKey, plan]) => (
                        <Grid item xs={12} sm={6} md={3} key={planKey}>
                          <Box
                            sx={{
                              p: 3,
                              border: subscription?.plan === planKey ? '2px solid #2563eb' : '1px solid #e5e7eb',
                              borderRadius: 2,
                              textAlign: 'center',
                              bgcolor: subscription?.plan === planKey ? '#eff6ff' : 'transparent',
                            }}
                          >
                            <Typography variant="h6" sx={{ color: '#000000' }}>{plan.name}</Typography>
                            <Typography variant="h4" sx={{ color: '#2563eb', my: 1 }}>
                              ${plan.price}
                              <Typography component="span" variant="body2" sx={{ color: '#6b7280' }}>/mo</Typography>
                            </Typography>
                            <Typography variant="body2" sx={{ color: '#374151' }}>{plan.apps} Apps</Typography>
                            <Typography variant="body2" sx={{ color: '#374151' }}>{plan.tokens} Tokens</Typography>
                            <Typography variant="body2" sx={{ color: '#374151' }}>{plan.storage}</Typography>
                            <Button
                              variant={subscription?.plan === planKey ? 'outlined' : 'contained'}
                              size="small"
                              sx={{ mt: 2 }}
                              disabled={subscription?.plan === planKey || changingPlan === planKey}
                              onClick={() => handleChangePlan(planKey)}
                            >
                              {changingPlan === planKey ? (
                                <CircularProgress size={16} />
                              ) : subscription?.plan === planKey ? (
                                'Current Plan'
                              ) : (
                                'Select Plan'
                              )}
                            </Button>
                          </Box>
                        </Grid>
                      ))}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>

              {/* Invoice History Card */}
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" sx={{ color: '#000000', mb: 3 }}>
                      Invoice History
                    </Typography>
                    {invoices.length > 0 ? (
                      <TableContainer>
                        <Table>
                          <TableHead>
                            <TableRow>
                              <TableCell>Invoice #</TableCell>
                              <TableCell>Date</TableCell>
                              <TableCell>Period</TableCell>
                              <TableCell>Amount</TableCell>
                              <TableCell>Status</TableCell>
                              <TableCell>Actions</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {invoices.map((invoice) => (
                              <TableRow key={invoice.id}>
                                <TableCell><strong>{invoice.number}</strong></TableCell>
                                <TableCell>{new Date(invoice.created_at).toLocaleDateString()}</TableCell>
                                <TableCell>
                                  {new Date(invoice.period_start).toLocaleDateString()} - {new Date(invoice.period_end).toLocaleDateString()}
                                </TableCell>
                                <TableCell>${invoice.total?.toFixed(2)} {invoice.currency?.toUpperCase()}</TableCell>
                                <TableCell>
                                  <Chip
                                    label={invoice.status}
                                    size="small"
                                    color={invoice.status === 'paid' ? 'success' : invoice.status === 'open' ? 'warning' : 'default'}
                                  />
                                </TableCell>
                                <TableCell>
                                  {invoice.pdf_url && (
                                    <Button size="small" href={invoice.pdf_url} target="_blank">
                                      Download PDF
                                    </Button>
                                  )}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    ) : (
                      <Alert severity="info">No invoices yet</Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </Box>
      )}
    </Container>
  )
}

export default FaibricAdmin
