import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Chip,
  Box,
  Dialog,
  DialogContent,
  CircularProgress,
} from '@mui/material'
import { api } from '../services/api'
import StripeCheckout from '../components/billing/StripeCheckout'

interface PlanDef {
  key: string
  name: string
  price: string
  features: string[]
  popular?: boolean
}

const plans: PlanDef[] = [
  {
    key: 'free',
    name: 'Free',
    price: '$0',
    features: ['3 apps', '50k AI tokens/month', '1GB storage', 'Community support'],
  },
  {
    key: 'starter',
    name: 'Starter',
    price: '$29',
    features: ['10 apps', '500k AI tokens/month', '10GB storage', 'Email support'],
  },
  {
    key: 'pro',
    name: 'Professional',
    price: '$79',
    popular: true,
    features: ['50 apps', '5M AI tokens/month', '50GB storage', 'Priority support'],
  },
  {
    key: 'enterprise',
    name: 'Enterprise',
    price: '$199',
    features: ['Unlimited apps', 'Unlimited AI tokens', '500GB storage', 'Dedicated support'],
  },
]

const Pricing = () => {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [currentPlan, setCurrentPlan] = useState<string>('free')
  const [loading, setLoading] = useState(true)
  const [checkoutPlan, setCheckoutPlan] = useState<PlanDef | null>(null)

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        const response = await api.get('/api/billing/subscription/')
        setCurrentPlan(response.data.plan || 'free')
      } catch {
        setCurrentPlan('free')
      } finally {
        setLoading(false)
      }
    }
    fetchSubscription()
  }, [])

  const handleUpgrade = (plan: PlanDef) => {
    setError('')
    setCheckoutPlan(plan)
  }

  const handleCheckoutSuccess = () => {
    setCheckoutPlan(null)
    navigate('/dashboard')
  }

  const handleCheckoutCancel = () => {
    setCheckoutPlan(null)
  }

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ bgcolor: '#ffffff', py: 4, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    )
  }

  return (
    <Container maxWidth="lg" sx={{ bgcolor: '#ffffff', py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Button variant="text" onClick={() => navigate('/dashboard')}>
          &larr; Back to Dashboard
        </Button>
      </Box>

      <Typography variant="h4" sx={{ color: '#000000', fontWeight: 600, textAlign: 'center', mb: 1 }}>
        Pricing Plans
      </Typography>
      <Typography variant="body1" sx={{ color: '#374151', textAlign: 'center', mb: 4 }}>
        Choose the plan that fits your needs
      </Typography>

      {error && (
        <Typography variant="body2" sx={{ color: 'error.main', textAlign: 'center', mb: 2 }}>
          {error}
        </Typography>
      )}

      <Grid container spacing={3}>
        {plans.map((plan) => (
          <Grid item xs={12} md={6} lg={3} key={plan.key}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                border: plan.popular ? '2px solid #1976d2' : '1px solid #e0e0e0',
                position: 'relative',
              }}
            >
              <CardContent sx={{ flexGrow: 1, textAlign: 'center', pt: plan.popular ? 4 : 3 }}>
                {plan.popular && (
                  <Chip
                    label="Most Popular"
                    color="primary"
                    size="small"
                    sx={{ position: 'absolute', top: 8, right: 8 }}
                  />
                )}
                <Typography variant="h5" sx={{ color: '#000000', fontWeight: 600, mb: 1 }}>
                  {plan.name}
                </Typography>
                <Typography variant="h4" sx={{ color: '#000000', fontWeight: 700, mb: 0.5 }}>
                  {plan.price}
                </Typography>
                <Typography variant="body2" sx={{ color: '#374151', mb: 3 }}>
                  /month
                </Typography>
                <Box sx={{ textAlign: 'left', mb: 3 }}>
                  {plan.features.map((feature) => (
                    <Typography key={feature} variant="body2" sx={{ color: '#374151', mb: 1 }}>
                      &bull; {feature}
                    </Typography>
                  ))}
                </Box>
                {plan.key === currentPlan ? (
                  <Button variant="outlined" fullWidth disabled>
                    Current Plan
                  </Button>
                ) : plan.key === 'free' ? (
                  <Button variant="outlined" fullWidth disabled>
                    Free Tier
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    fullWidth
                    onClick={() => handleUpgrade(plan)}
                  >
                    Upgrade
                  </Button>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog
        open={checkoutPlan !== null}
        onClose={handleCheckoutCancel}
        maxWidth="sm"
        fullWidth
      >
        <DialogContent sx={{ p: 0 }}>
          {checkoutPlan && (
            <StripeCheckout
              planKey={checkoutPlan.key}
              planName={checkoutPlan.name}
              onSuccess={handleCheckoutSuccess}
              onCancel={handleCheckoutCancel}
            />
          )}
        </DialogContent>
      </Dialog>
    </Container>
  )
}

export default Pricing
