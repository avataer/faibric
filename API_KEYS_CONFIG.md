# Faibric API Keys Configuration

## How to Set Up

1. Copy the environment variables below to your `.env` file
2. Fill in your actual API keys
3. The system automatically uses **mock responses** when keys are empty

---

## Required API Keys

### LLM Providers (AI Code Generation)

| Key | Service | Purpose | Get It |
|-----|---------|---------|--------|
| `ANTHROPIC_API_KEY` | Anthropic | Claude Opus 4.5 for code generation | https://console.anthropic.com/ |
| `OPENAI_API_KEY` | OpenAI | Embeddings for code search | https://platform.openai.com/ |

### Payment Processing

| Key | Service | Purpose | Get It |
|-----|---------|---------|--------|
| `STRIPE_SECRET_KEY` | Stripe | Subscription billing | https://dashboard.stripe.com/apikeys |
| `STRIPE_PUBLISHABLE_KEY` | Stripe | Frontend checkout | https://dashboard.stripe.com/apikeys |
| `STRIPE_WEBHOOK_SECRET` | Stripe | Webhook verification | Stripe Dashboard > Webhooks |
| `PAYPAL_CLIENT_ID` | PayPal | Alternative payments | https://developer.paypal.com/ |
| `PAYPAL_CLIENT_SECRET` | PayPal | Alternative payments | https://developer.paypal.com/ |

### Google Services

| Key | Service | Purpose | Get It |
|-----|---------|---------|--------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads | Ad campaign management | https://ads.google.com/aw/apicenter |
| `GOOGLE_ADS_CLIENT_ID` | Google Ads | OAuth | Google Cloud Console |
| `GOOGLE_ADS_CLIENT_SECRET` | Google Ads | OAuth | Google Cloud Console |
| `GOOGLE_ADS_REFRESH_TOKEN` | Google Ads | OAuth | OAuth flow |
| `GOOGLE_ADS_CUSTOMER_ID` | Google Ads | Your account ID | Google Ads dashboard |

### Email Services

| Key | Service | Purpose | Get It |
|-----|---------|---------|--------|
| `SENDGRID_API_KEY` | SendGrid | Magic links, notifications | https://app.sendgrid.com/settings/api_keys |

### Other Services

| Key | Service | Purpose | Get It |
|-----|---------|---------|--------|
| `SERPAPI_KEY` | SerpAPI | Keyword rank tracking | https://serpapi.com/ |
| `MIXPANEL_TOKEN` | Mixpanel | Analytics events | https://mixpanel.com/ |

---

## Environment Variables Template

```bash
# LLM Providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

# PayPal
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_CUSTOMER_ID=

# Email
SENDGRID_API_KEY=

# Other
SERPAPI_KEY=
MIXPANEL_TOKEN=

# App Settings
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production
FRONTEND_URL=http://localhost:5173
```

---

## Mock Mode

When API keys are empty or missing, Faibric automatically uses mock responses.
This allows you to test the full system without paying for services.

The mock system:
- Returns realistic fake data
- Simulates delays like real APIs
- Logs all "calls" for debugging
- Works identically to real APIs (same response format)







