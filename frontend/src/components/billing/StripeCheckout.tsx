import { useState } from 'react'
import { loadStripe } from '@stripe/stripe-js'
import {
  Elements,
  CardElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js'
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Paper,
} from '@mui/material'
import api from '../../services/api'

const stripePromise = loadStripe(
  import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || ''
)

interface StripeCheckoutProps {
  planKey: string
  planName: string
  onSuccess: () => void
  onCancel: () => void
}

interface CheckoutFormProps {
  planKey: string
  planName: string
  onSuccess: () => void
  onCancel: () => void
}

const CARD_ELEMENT_OPTIONS = {
  style: {
    base: {
      fontSize: '16px',
      color: '#374151',
      '::placeholder': {
        color: '#9ca3af',
      },
    },
    invalid: {
      color: '#ef4444',
    },
  },
}

const CheckoutForm = ({ planKey, planName, onSuccess, onCancel }: CheckoutFormProps) => {
  const stripe = useStripe()
  const elements = useElements()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()

    if (!stripe || !elements) {
      return
    }

    const cardElement = elements.getElement(CardElement)
    if (!cardElement) {
      return
    }

    setLoading(true)
    setError(null)

    try {
      const { error: stripeError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      })

      if (stripeError) {
        setError(stripeError.message || 'Payment failed')
        setLoading(false)
        return
      }

      const response = await api.post('/api/billing/subscription/change-plan/', {
        plan: planKey,
        payment_method_id: paymentMethod.id,
      })

      if (response.data.client_secret) {
        const { error: confirmError } = await stripe.confirmCardPayment(
          response.data.client_secret
        )

        if (confirmError) {
          setError(confirmError.message || 'Payment confirmation failed')
          setLoading(false)
          return
        }
      }

      onSuccess()
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'An unexpected error occurred'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Paper sx={{ p: 4, maxWidth: 480 }}>
      <Typography variant="h6" fontWeight={600} sx={{ mb: 1 }}>
        Subscribe to {planName}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Enter your payment details below.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <Box
          sx={{
            border: '1px solid #e5e7eb',
            borderRadius: 1,
            p: 2,
            mb: 3,
          }}
        >
          <CardElement options={CARD_ELEMENT_OPTIONS} />
        </Box>

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
          <Button
            variant="outlined"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!stripe || loading}
            startIcon={loading ? <CircularProgress size={16} /> : undefined}
          >
            {loading ? 'Processing...' : 'Subscribe'}
          </Button>
        </Box>
      </form>
    </Paper>
  )
}

const StripeCheckout = ({ planKey, planName, onSuccess, onCancel }: StripeCheckoutProps) => {
  return (
    <Elements stripe={stripePromise}>
      <CheckoutForm
        planKey={planKey}
        planName={planName}
        onSuccess={onSuccess}
        onCancel={onCancel}
      />
    </Elements>
  )
}

export default StripeCheckout
