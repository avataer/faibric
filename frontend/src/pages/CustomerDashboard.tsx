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
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material'
import { api } from '../services/api'

interface CreditBalance {
  credits_remaining: number
  credits_used: number
  total_credits: number
  subscription_tier: string
  tier_price: string
  renewal_date: string
}

interface UsageRecord {
  id: string
  project_name: string
  action: string
  tokens: number
  credits: number
  timestamp: string
}

interface Subscription {
  tier_name: string
  price: string
  credits_per_month: number
  features: string[]
  status: string
}

interface BillingHistory {
  id: string
  date: string
  description: string
  amount: string
  status: string
}

const CustomerDashboard = () => {
  const [tab, setTab] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Data states
  const [creditBalance, setCreditBalance] = useState<CreditBalance | null>(null)
  const [usageHistory, setUsageHistory] = useState<UsageRecord[]>([])
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [billingHistory, setBillingHistory] = useState<BillingHistory[]>([])

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [balanceRes, usageRes, subRes, billingRes] = await Promise.all([
        api.get('/api/credits/balance/'),
        api.get('/api/credits/usage/'),
        api.get('/api/credits/subscription/'),
        api.get('/api/billing/usage/history/'),
      ].map(p => p.catch(e => ({ data: null, error: e }))))

      if (balanceRes.data) setCreditBalance(balanceRes.data)
      if (usageRes.data) setUsageHistory(usageRes.data.results || usageRes.data || [])
      if (subRes.data) setSubscription(subRes.data)
      if (billingRes.data) setBillingHistory(billingRes.data.results || billingRes.data || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  const usagePercent = creditBalance 
    ? (creditBalance.credits_used / creditBalance.total_credits) * 100 
    : 0

  // Mock data for testing when API returns nothing
  const displayBalance = creditBalance || {
    credits_remaining: 847,
    credits_used: 153,
    total_credits: 1000,
    subscription_tier: 'Pro',
    tier_price: '$99.99',
    renewal_date: 'Dec 28, 2025',
  }
  
  const displaySubscription = subscription || {
    tier_name: 'Pro',
    price: '$99.99',
    credits_per_month: 1000,
    features: ['Unlimited projects', 'Priority support', 'Custom domains', 'Team collaboration'],
    status: 'active',
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4, bgcolor: '#ffffff' }}>
      <Typography variant="h4" sx={{ color: '#000000', fontWeight: 700, mb: 1 }}>
        My Account
      </Typography>
      <Typography variant="body1" sx={{ color: '#374151', mb: 4 }}>
        Manage your credits, subscription, and billing
      </Typography>

      {error && (
        <Alert severity="warning" sx={{ mb: 3 }}>Using demo data - {error}</Alert>
      )}

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#000000' }}>
                {displayBalance.credits_remaining}
              </Typography>
              <Typography variant="body2" sx={{ color: '#374151' }}>
                Credits Remaining
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#000000' }}>
                {displayBalance.credits_used}
              </Typography>
              <Typography variant="body2" sx={{ color: '#374151' }}>
                Credits Used (MTD)
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h5" sx={{ color: '#2563eb' }}>
                {displaySubscription.tier_name}
              </Typography>
              <Typography variant="body2" sx={{ color: '#374151' }}>
                Current Plan
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h5" sx={{ color: '#000000' }}>
                {displaySubscription.price}/mo
              </Typography>
              <Typography variant="body2" sx={{ color: '#374151' }}>
                Monthly Cost
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Usage Progress */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="subtitle1" sx={{ color: '#000000' }}>Monthly Credit Usage</Typography>
            <Typography variant="body2" sx={{ color: '#374151' }}>
              {displayBalance.credits_used} / {displayBalance.total_credits} credits
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={(displayBalance.credits_used / displayBalance.total_credits) * 100} 
            sx={{ height: 12, borderRadius: 6 }}
          />
          <Typography variant="caption" sx={{ color: '#374151', mt: 1, display: 'block' }}>
            Renews: {displayBalance.renewal_date}
          </Typography>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Usage History" />
        <Tab label="Subscription" />
        <Tab label="Billing" />
        <Tab label="My Google Ads" />
      </Tabs>

      {/* Tab Content */}
      {tab === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>Recent Usage</Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Project</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Tokens</TableCell>
                    <TableCell>Credits</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {usageHistory.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography sx={{ color: '#374151', py: 3 }}>
                          No usage history yet. Start building to see your usage here.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : usageHistory.map((record) => (
                    <TableRow key={record.id}>
                      <TableCell>{new Date(record.timestamp).toLocaleString()}</TableCell>
                      <TableCell><strong>{record.project_name}</strong></TableCell>
                      <TableCell>{record.action}</TableCell>
                      <TableCell>{record.tokens?.toLocaleString()}</TableCell>
                      <TableCell>
                        <Chip label={`${record.credits} credits`} size="small" color="primary" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {tab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>Current Plan</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, mb: 3 }}>
                  <Box sx={{ 
                    p: 3, 
                    border: '2px solid #2563eb',
                    borderRadius: 2, 
                    textAlign: 'center',
                    minWidth: 120,
                  }}>
                    <Typography variant="h5" sx={{ color: '#000000', fontWeight: 700 }}>
                      {displaySubscription.tier_name}
                    </Typography>
                    <Typography variant="h4" sx={{ color: '#2563eb' }}>
                      {displaySubscription.price}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#374151' }}>/month</Typography>
                  </Box>
                  <Box>
                    <Typography variant="body1" sx={{ color: '#000000', mb: 1 }}>
                      <strong>{displaySubscription.credits_per_month}</strong> credits per month
                    </Typography>
                    <Chip 
                      label={displaySubscription.status === 'active' ? 'Active' : 'Inactive'} 
                      color={displaySubscription.status === 'active' ? 'success' : 'default'}
                      size="small"
                    />
                  </Box>
                </Box>
                
                <Divider sx={{ my: 2 }} />
                
                <Typography variant="subtitle2" sx={{ color: '#000000', mb: 1 }}>Plan Features:</Typography>
                <List dense>
                  {displaySubscription.features.map((feature, idx) => (
                    <ListItem key={idx}>
                      <ListItemText primary={feature} sx={{ '& .MuiListItemText-primary': { color: '#374151' } }} />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>Upgrade Plan</Typography>
                <Typography variant="body2" sx={{ color: '#374151', mb: 2 }}>
                  Get more credits and features
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Button variant="outlined" fullWidth>
                    Basic - $19.99/mo
                  </Button>
                  <Button variant="contained" fullWidth>
                    Pro - $99.99/mo
                  </Button>
                </Box>
              </CardContent>
            </Card>
            
            <Card sx={{ mt: 2 }}>
              <CardContent>
                <Typography variant="h6" sx={{ color: '#000000', mb: 2 }}>Buy Credits</Typography>
                <Typography variant="body2" sx={{ color: '#374151', mb: 2 }}>
                  Need more credits right now?
                </Typography>
                <Button variant="contained" color="success" fullWidth>
                  Buy 500 Credits - $49.99
                </Button>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {tab === 2 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
              <Typography variant="h6" sx={{ color: '#000000' }}>Billing History</Typography>
              <Button variant="outlined">
                Payment Methods
              </Button>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Amount</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Invoice</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {billingHistory.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography sx={{ color: '#374151', py: 3 }}>
                          No billing history yet.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : billingHistory.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>{item.date}</TableCell>
                      <TableCell>{item.description}</TableCell>
                      <TableCell><strong>{item.amount}</strong></TableCell>
                      <TableCell>
                        <Chip 
                          label={item.status} 
                          size="small"
                          color={item.status === 'paid' ? 'success' : 'warning'}
                        />
                      </TableCell>
                      <TableCell>
                        <Button size="small">Download</Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {tab === 3 && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
              <Typography variant="h6" sx={{ color: '#000000' }}>My Google Ads Campaigns</Typography>
              <Button variant="contained">
                Create Campaign
              </Button>
            </Box>
            <Alert severity="info" sx={{ mb: 3 }}>
              Connect your Google Ads account to run ads for your projects and track results here.
            </Alert>
            <Button variant="outlined" size="large">
              Connect Google Ads Account
            </Button>
          </CardContent>
        </Card>
      )}
    </Container>
  )
}

export default CustomerDashboard
