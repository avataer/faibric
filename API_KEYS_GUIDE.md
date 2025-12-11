# Faibric API Keys Guide

This document explains which API keys are needed, who provides them, and what they're used for.

---

## LLM Strategy

Faibric uses the **optimal LLM for each task type**:

| Task | Model | Why |
|------|-------|-----|
| **Code Generation** | Claude Opus 4.5 | Best code quality, understands complex requirements |
| **Code Modification** | Claude Opus 4.5 | Maintains consistency, careful edits |
| **Code Analysis** | Claude Opus 4.5 | Thorough, catches edge cases |
| **AI Chat** | Claude Sonnet 4 | Fast + smart, great for conversations |
| **Summarization** | Claude Haiku 3.5 | Ultra fast for simple tasks |
| **Embeddings** | OpenAI text-embedding-3-small | Best semantic search quality |

---

## Overview: Three Types of API Keys

| Type | Provider | Purpose | Who Pays |
|------|----------|---------|----------|
| 🔵 **Platform Keys** | Faibric (You) | Power the platform for all customers | Faibric |
| 🟢 **Customer Keys** | Customers | Power their own apps/businesses | Customers |
| 🟡 **Shared Keys** | Either | Can use Faibric's (via credits) or their own | Depends |

---

## 🔵 PLATFORM KEYS (You Provide)

These are Faibric's own API keys that power the entire platform. Customers access these services through Faibric and pay via credits/subscriptions.

### Required for Core Functionality

| Service | Key Name | Purpose | Get From |
|---------|----------|---------|----------|
| **Anthropic** | `ANTHROPIC_API_KEY` | Claude Opus 4.5 for code generation, Sonnet for chat | [Anthropic Console](https://console.anthropic.com/) |
| **OpenAI** | `OPENAI_API_KEY` | Embeddings for semantic search | [OpenAI Platform](https://platform.openai.com/api-keys) |
| **Stripe** | `STRIPE_SECRET_KEY` | Customer subscriptions, billing | [Stripe Dashboard](https://dashboard.stripe.com/apikeys) |
| **Stripe Webhook** | `STRIPE_WEBHOOK_SECRET` | Payment event notifications | Stripe Dashboard → Webhooks |
| **SendGrid** | `SENDGRID_API_KEY` | System emails (welcome, receipts) | [SendGrid](https://app.sendgrid.com/settings/api_keys) |
| **Database** | `DATABASE_URL` | PostgreSQL connection | Your hosting provider |
| **Redis** | `REDIS_URL` | Caching, Celery queue | Your hosting provider |

### Optional for Enhanced Features

| Service | Key Name | Purpose | Get From |
|---------|----------|---------|----------|
| **AWS S3** | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | File storage | [AWS Console](https://console.aws.amazon.com/iam/) |
| **Mixpanel** | `MIXPANEL_TOKEN` | Faibric analytics dashboard | [Mixpanel](https://mixpanel.com/) |
| **Google Ads** | `GOOGLE_ADS_*` | Faibric's own ad campaigns | [Google Ads API](https://developers.google.com/google-ads/api/docs/first-call/oauth-cloud-project) |

---

## 🟢 CUSTOMER KEYS (Customers Provide)

Customers add these to their tenant settings to power their own apps. These are optional - they can use Faibric's services via credits instead.

### Payment Processing (For Their Business)

| Service | Key Name | Purpose |
|---------|----------|---------|
| **Stripe** | Customer's own Stripe keys | Sell products to their end-users |
| **PayPal** | Customer's PayPal keys | Alternative payment for their users |

### Communication (For Their Users)

| Service | Key Name | Purpose |
|---------|----------|---------|
| **SendGrid/Email** | Customer's email API key | Newsletters, transactional emails |
| **Twilio** | Customer's Twilio keys | SMS notifications to their users |

### Analytics & Marketing (For Their Business)

| Service | Key Name | Purpose |
|---------|----------|---------|
| **Google Analytics** | Customer's GA ID | Track their app analytics |
| **Google Ads** | Customer's Google Ads API | Run their own ad campaigns |
| **Mixpanel** | Customer's Mixpanel token | Their event analytics |

---

## 🟡 SHARED/OPTIONAL (Either Can Provide)

These services can work two ways:
1. **Via Faibric**: Customer uses Faibric's API keys and pays via credits
2. **Via Their Own Keys**: Customer brings their own keys and pays directly

### AI/LLM Services

| Scenario | How It Works |
|----------|--------------|
| **Faibric's Keys (Default)** | Customer uses GPT-4, Claude via Faibric. Faibric pays OpenAI/Anthropic. Customer pays Faibric credits. |
| **Customer's Keys** | Customer adds own OpenAI key in settings. Requests go to their account. They pay OpenAI directly. |

### Email/SMS

| Scenario | How It Works |
|----------|--------------|
| **Faibric's Keys (Default)** | Emails sent from `noreply@faibric.com`. Basic limits apply. |
| **Customer's Keys** | Customer adds own SendGrid key. Emails from their domain. No limits. |

---

## Environment Variables (.env)

```bash
# ===========================================
# FAIBRIC PLATFORM KEYS (Required)
# ===========================================

# LLM - Both required for full functionality
ANTHROPIC_API_KEY=sk-ant-...             # Required - Claude Opus 4.5 for code gen
OPENAI_API_KEY=sk-...                    # Required - Embeddings only

# Payments - Faibric's Stripe account
STRIPE_SECRET_KEY=sk_live_...            # Required
STRIPE_PUBLISHABLE_KEY=pk_live_...       # Required
STRIPE_WEBHOOK_SECRET=whsec_...          # Required

# Email
SENDGRID_API_KEY=SG....                  # Required for emails

# Database
DATABASE_URL=postgres://user:pass@host:5432/faibric

# Cache/Queue
REDIS_URL=redis://localhost:6379

# ===========================================
# FAIBRIC PLATFORM KEYS (Optional)
# ===========================================

# Storage (defaults to local if not set)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=faibric-storage
AWS_S3_REGION=us-east-1

# OR Cloudflare R2
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Analytics (for Faibric admin dashboard)
MIXPANEL_TOKEN=                          # Faibric's own analytics
GA_MEASUREMENT_ID=                       # Faibric's Google Analytics

# Google Ads (for Faibric's own campaigns)
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_CUSTOMER_ID=

# ===========================================
# APPLICATION SETTINGS
# ===========================================

SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=faibric.com,api.faibric.com

# Frontend URL (for CORS, emails)
FRONTEND_URL=https://faibric.com
```

---

## How Credits Work

### Subscription Tiers

| Tier | Price | Credits/Month | Ideal For |
|------|-------|--------------|-----------|
| **Free** | $0 | 50 | Trying out Faibric |
| **Starter** | $19.99/mo | 500 | Individual developers |
| **Pro** | $99.99/mo | 5,000 | Teams & agencies |

### Credit Usage

| Action | Credits | Notes |
|--------|---------|-------|
| 1 Code Generation Request | 1 credit | Plus tokens tracked |
| 1 AI Chat Message | 1 credit | Plus tokens tracked |
| 1 Code Modification | 1 credit | Plus tokens tracked |

Customers can:
- See usage in their dashboard (`/api/credits/balance/summary/`)
- Purchase additional credits anytime
- View detailed token/request history

---

## Setup Steps

### 1. Set Up Required Keys

```bash
# 1. Anthropic - Get from console.anthropic.com
#    This powers Claude Opus 4.5 for code generation
ANTHROPIC_API_KEY=sk-ant-...

# 2. OpenAI - Get from platform.openai.com
#    Used for embeddings only (semantic search)
OPENAI_API_KEY=sk-proj-...

# 3. Stripe - Get from dashboard.stripe.com
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...

# 4. Create Stripe webhook at dashboard.stripe.com/webhooks
#    Point to: https://api.faibric.com/api/billing/webhooks/stripe/
STRIPE_WEBHOOK_SECRET=whsec_...

# 5. SendGrid - Get from app.sendgrid.com
SENDGRID_API_KEY=SG...

# 6. Database and Redis
DATABASE_URL=postgres://...
REDIS_URL=redis://...
```

### 2. Create Subscription Products in Stripe

Run this management command after setting up Stripe:

```bash
python manage.py setup_stripe_products
```

This creates:
- Free tier (no charge)
- Starter tier ($19.99/month)
- Pro tier ($99.99/month)

### 3. Set Up Google Ads (Optional)

For Faibric's own marketing:

1. Create Google Cloud Project
2. Enable Google Ads API
3. Create OAuth credentials
4. Get developer token from ads.google.com
5. Complete OAuth flow for refresh token

```bash
GOOGLE_ADS_DEVELOPER_TOKEN=...
GOOGLE_ADS_CLIENT_ID=...
GOOGLE_ADS_CLIENT_SECRET=...
GOOGLE_ADS_REFRESH_TOKEN=...
GOOGLE_ADS_CUSTOMER_ID=...
```

---

## Customer API Key Management

Customers can add their own API keys in their tenant settings:

**Endpoint**: `PUT /api/tenants/settings/api-keys/`

```json
{
  "stripe_secret_key": "sk_live_...",
  "stripe_publishable_key": "pk_live_...",
  "paypal_client_id": "...",
  "paypal_secret": "...",
  "sendgrid_api_key": "SG...",
  "twilio_account_sid": "...",
  "twilio_auth_token": "...",
  "google_analytics_id": "G-...",
  "google_ads_customer_id": "..."
}
```

When customers add their own keys:
- Those services use their keys directly
- No credits are charged for those services
- They're billed directly by the provider

---

## Summary: What You Need to Provide

### Minimum to Launch (Required)
1. ✅ `ANTHROPIC_API_KEY` - For Claude Opus 4.5 (code generation)
2. ✅ `OPENAI_API_KEY` - For embeddings (semantic search)
3. ✅ `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` - For billing
4. ✅ `SENDGRID_API_KEY` - For emails
5. ✅ `DATABASE_URL` - PostgreSQL
6. ✅ `REDIS_URL` - For cache/queue

### Recommended Additions
7. 🟡 `AWS_*` or `R2_*` - Cloud storage
8. 🟡 `MIXPANEL_TOKEN` - Analytics dashboard
9. 🟡 `GOOGLE_ADS_*` - For marketing Faibric

### Customer-Provided (Not Your Keys)
- Stripe/PayPal for their checkout
- SendGrid/Twilio for their communications
- Google Analytics/Ads for their marketing

---

## LLM Cost Breakdown

| Model | Usage | Cost per 1K Input | Cost per 1K Output |
|-------|-------|-------------------|-------------------|
| Claude Opus 4.5 | Code generation, analysis | $0.015 | $0.075 |
| Claude Sonnet 4 | AI Chat | $0.003 | $0.015 |
| Claude Haiku 3.5 | Quick tasks | $0.0008 | $0.004 |
| OpenAI Embeddings | Semantic search | $0.00002 | N/A |

**Example costs for 1 code generation request:**
- Average input: ~500 tokens → $0.0075
- Average output: ~2000 tokens → $0.15
- **Total Faibric cost: ~$0.16 per request**

With customers paying 1 credit per request, and credit packs priced accordingly, this ensures profitability.

---

## Questions?

- **"Why Claude Opus 4.5 for code?"** - It's the best model for complex code generation, understands context deeply, and produces clean, well-documented code.
- **"Why OpenAI for embeddings?"** - text-embedding-3-small is the best embedding model for semantic search, and it's very cheap.
- **"Where do customer payments go?"** - Subscription payments go to YOUR Stripe. Their end-user payments go to THEIR Stripe.

