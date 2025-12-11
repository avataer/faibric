# Faibric V3: Universal App Builder Architecture

## The Problem

Current architecture CANNOT handle real-world use cases because:
1. Generated apps are static React frontends with NO backend capability
2. External API calls fail due to CORS (browser security blocks cross-origin requests)
3. Every new use case requires manual backend endpoint creation
4. No API key management - users can't provide their own keys
5. No database access for generated apps
6. No authentication/user management for generated apps

**This is fundamentally broken. A customer asking for a "stock dashboard" shouldn't require manual intervention.**

---

## The Solution: Full-Stack Generation + Universal Backend

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FAIBRIC PLATFORM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────────┐    │
│  │   Frontend   │    │   Faibric Core   │    │   API Key Vault    │    │
│  │   (React)    │───▶│   Backend        │───▶│   (Encrypted)      │    │
│  │              │    │   (Django)       │    │                    │    │
│  └──────────────┘    └────────┬─────────┘    └────────────────────┘    │
│                               │                                          │
│                               ▼                                          │
│                    ┌──────────────────────┐                             │
│                    │   Universal Gateway   │                             │
│                    │   /api/gateway/       │                             │
│                    │                       │                             │
│                    │ • HTTP Proxy          │                             │
│                    │ • API Key Injection   │                             │
│                    │ • Rate Limiting       │                             │
│                    │ • Caching             │                             │
│                    │ • Request Transform   │                             │
│                    └───────────┬───────────┘                             │
│                                │                                          │
├────────────────────────────────┼────────────────────────────────────────┤
│         GENERATED APPS         │                                          │
│                                ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Per-App Backend (Optional)                     │    │
│  │                                                                   │    │
│  │  For complex apps that need:                                      │    │
│  │  • Database (PostgreSQL/SQLite per app)                          │    │
│  │  • User authentication                                            │    │
│  │  • Custom business logic                                          │    │
│  │  • Scheduled tasks                                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    Generated Frontend                             │    │
│  │                                                                   │    │
│  │  • React SPA                                                      │    │
│  │  • Calls Universal Gateway OR Per-App Backend                    │    │
│  │  • Never calls external APIs directly                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Universal Gateway (`/api/gateway/`)

A single endpoint that can proxy ANY HTTP request to ANY external service.

```python
# Example usage from generated app:
fetch('http://faibric.localhost/api/gateway/', {
  method: 'POST',
  headers: { 'X-App-Token': 'app-token-123' },
  body: JSON.stringify({
    service: 'openweather',  // Pre-configured service
    endpoint: '/weather',
    params: { q: 'London', units: 'metric' }
  })
})

# Or for arbitrary URLs:
fetch('http://faibric.localhost/api/gateway/', {
  method: 'POST', 
  body: JSON.stringify({
    url: 'https://api.example.com/data',
    method: 'GET',
    headers: { 'Authorization': 'Bearer ${API_KEY}' }  // Injected from vault
  })
})
```

**Features:**
- Proxies requests to external APIs (bypasses CORS)
- Automatically injects API keys from vault
- Rate limiting per app/user
- Response caching
- Request/response transformation
- Audit logging

### 2. API Key Vault

Secure storage for API keys with hierarchical access:

```
Platform Keys (available to all apps):
  - OPENWEATHER_API_KEY
  - ALPHA_VANTAGE_API_KEY
  - NEWS_API_KEY
  - etc.

User Keys (per Faibric user):
  - user's own OpenAI key
  - user's Stripe key
  - etc.

App Keys (per generated app):
  - app-specific secrets
```

### 3. Service Registry

Pre-configured integrations for common services:

```yaml
services:
  openweather:
    base_url: https://api.openweathermap.org/data/2.5
    auth_type: query_param
    auth_param: appid
    key_name: OPENWEATHER_API_KEY
    
  alpha_vantage:
    base_url: https://www.alphavantage.co/query
    auth_type: query_param
    auth_param: apikey
    key_name: ALPHA_VANTAGE_API_KEY
    
  newsapi:
    base_url: https://newsapi.org/v2
    auth_type: header
    auth_header: X-Api-Key
    key_name: NEWS_API_KEY
    
  stripe:
    base_url: https://api.stripe.com/v1
    auth_type: bearer
    key_name: STRIPE_SECRET_KEY
    requires_user_key: true  # User must provide their own
    
  openai:
    base_url: https://api.openai.com/v1
    auth_type: bearer
    key_name: OPENAI_API_KEY
    
  # ... many more
```

### 4. Enhanced AI Prompts

The AI must be instructed to ALWAYS use the gateway:

```python
UNIVERSAL_PROMPT = """
You are building an app for Faibric platform.

CRITICAL RULES FOR EXTERNAL DATA:
1. NEVER use fetch() to call external APIs directly - it will fail due to CORS
2. ALWAYS use the Faibric Gateway for external data:

   // For pre-configured services:
   const response = await fetch('/api/gateway/', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       service: 'openweather',  // or: alpha_vantage, newsapi, etc.
       endpoint: '/weather',
       params: { q: 'London' }
     })
   });
   
   // For custom APIs:
   const response = await fetch('/api/gateway/', {
     method: 'POST',
     body: JSON.stringify({
       url: 'https://api.example.com/data',
       method: 'GET'
     })
   });

3. Available pre-configured services:
   - openweather: Weather data (current, forecast)
   - alpha_vantage: Stock prices, crypto, forex
   - newsapi: News articles
   - exchangerate: Currency exchange rates
   - github: GitHub API
   - ... (see full list)

4. Always handle loading and error states
5. Use realistic fallback/demo data if API fails
"""
```

---

## Implementation Plan

### Phase 1: Universal Gateway (IMMEDIATE - 2 hours)

1. Create `/api/gateway/` endpoint
2. Implement service registry with 5-10 common services
3. Add API key vault (simple encrypted storage)
4. Update AI prompts to use gateway

### Phase 2: Full-Stack Generation (NEXT - 4 hours)

1. Option to generate backend (FastAPI/Express) alongside frontend
2. Per-app database support (SQLite embedded)
3. Per-app authentication
4. Deploy as single container with both frontend + backend

### Phase 3: Advanced Features (FUTURE)

1. Scheduled tasks for generated apps
2. Webhooks support
3. WebSocket connections
4. File storage
5. Email sending

---

## API Keys Required

### Platform Keys (Faibric provides - FREE TIERS)

| Service | Key Name | Free Tier | Sign Up |
|---------|----------|-----------|---------|
| OpenWeather | OPENWEATHER_API_KEY | 1000 calls/day | https://openweathermap.org/api |
| Alpha Vantage | ALPHA_VANTAGE_API_KEY | 5 calls/min | https://www.alphavantage.co/support/#api-key |
| News API | NEWS_API_KEY | 100 calls/day | https://newsapi.org/register |
| Exchange Rate | EXCHANGE_RATE_API_KEY | 1500 calls/month | https://www.exchangerate-api.com/ |
| Unsplash | UNSPLASH_ACCESS_KEY | 50 calls/hour | https://unsplash.com/developers |
| Giphy | GIPHY_API_KEY | Unlimited (with attribution) | https://developers.giphy.com/ |

### User-Provided Keys (For premium/specific services)

| Service | When Needed | User Sign Up |
|---------|-------------|--------------|
| Stripe | E-commerce apps | https://stripe.com |
| Twilio | SMS/Voice apps | https://twilio.com |
| SendGrid | Email apps | https://sendgrid.com |
| Google Maps | Location apps | https://console.cloud.google.com |
| OpenAI | AI-powered apps | https://platform.openai.com |

---

## Database Schema Updates

```sql
-- API Key Vault
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    encrypted_value TEXT NOT NULL,
    scope VARCHAR(20) NOT NULL,  -- 'platform', 'user', 'app'
    user_id INTEGER REFERENCES users(id),
    app_id INTEGER REFERENCES projects(id),
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Service Registry
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    base_url VARCHAR(500) NOT NULL,
    auth_type VARCHAR(50),  -- 'bearer', 'query_param', 'header', 'basic'
    auth_config JSONB,
    key_name VARCHAR(100),
    requires_user_key BOOLEAN DEFAULT FALSE,
    rate_limit INTEGER,
    rate_limit_window INTEGER,  -- seconds
    created_at TIMESTAMP DEFAULT NOW()
);

-- Request Audit Log
CREATE TABLE gateway_requests (
    id SERIAL PRIMARY KEY,
    app_id INTEGER REFERENCES projects(id),
    user_id INTEGER REFERENCES users(id),
    service VARCHAR(100),
    endpoint VARCHAR(500),
    method VARCHAR(10),
    status_code INTEGER,
    response_time_ms INTEGER,
    cached BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## File Structure

```
backend/
├── apps/
│   ├── gateway/                    # NEW: Universal Gateway
│   │   ├── __init__.py
│   │   ├── views.py               # Gateway endpoint
│   │   ├── services.py            # Service registry logic
│   │   ├── vault.py               # API key management
│   │   ├── proxy.py               # HTTP proxy logic
│   │   ├── cache.py               # Response caching
│   │   └── urls.py
│   │
│   ├── vault/                      # NEW: API Key Vault
│   │   ├── __init__.py
│   │   ├── models.py              # APIKey, Service models
│   │   ├── encryption.py          # Key encryption
│   │   ├── views.py               # Key management API
│   │   └── urls.py
│   │
│   └── ai_engine/
│       └── v3/                     # NEW: V3 Generator
│           ├── prompts.py         # Updated prompts with gateway
│           ├── generator.py       # Full-stack generation
│           └── tasks.py
```

---

## Quick Test After Implementation

```bash
# 1. Test gateway with weather
curl -X POST http://localhost:8000/api/gateway/ \
  -H "Content-Type: application/json" \
  -d '{"service": "openweather", "endpoint": "/weather", "params": {"q": "London"}}'

# 2. Test gateway with stocks
curl -X POST http://localhost:8000/api/gateway/ \
  -H "Content-Type: application/json" \
  -d '{"service": "alpha_vantage", "endpoint": "", "params": {"function": "GLOBAL_QUOTE", "symbol": "AAPL"}}'

# 3. Create test app
curl -X POST http://localhost:8000/api/projects/ \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "WeatherApp", "user_prompt": "Create a weather dashboard showing current weather for 5 major cities"}'
```

---

## ACTION ITEMS FOR USER

### Immediate (Do Tonight/Tomorrow):

1. **Sign up for free API keys** (5 minutes each):

   - [ ] **OpenWeather**: https://openweathermap.org/api
     - Click "Sign Up" → Verify email → Go to "API Keys" tab → Copy key
   
   - [ ] **Alpha Vantage**: https://www.alphavantage.co/support/#api-key
     - Fill form → Get key instantly (no email verification)
   
   - [ ] **News API**: https://newsapi.org/register
     - Sign up → Verify email → Copy key from dashboard
   
   - [ ] **Exchange Rate API**: https://www.exchangerate-api.com/
     - Enter email → Get key instantly

2. **Create `.env` file** in `/Users/abram/Code/Faibric/`:

```bash
# Platform API Keys
OPENWEATHER_API_KEY=your_key_here
ALPHA_VANTAGE_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
EXCHANGE_RATE_API_KEY=your_key_here

# Already have
OPENAI_API_KEY=your_existing_key
```

3. **Optional but recommended**:
   - [ ] **Unsplash** (for image-heavy apps): https://unsplash.com/developers
   - [ ] **Giphy** (for GIF apps): https://developers.giphy.com/

---

## What This Enables

After implementation, customers can ask for:

| Request | How It Works |
|---------|--------------|
| "Stock dashboard" | Uses Alpha Vantage via gateway |
| "Weather app" | Uses OpenWeather via gateway |
| "News aggregator" | Uses News API via gateway |
| "Currency converter" | Uses Exchange Rate API via gateway |
| "Recipe finder" | Uses Spoonacular via gateway |
| "Movie database" | Uses TMDB via gateway |
| "E-commerce store" | Uses Stripe (user provides key) |
| "Chat application" | Uses OpenAI (user provides key) |
| "Any custom API" | Uses arbitrary URL via gateway |

**No manual intervention required. No CORS issues. Real data always.**

---

## Summary

The current architecture is fundamentally incapable of handling real-world use cases. This V3 architecture fixes it by:

1. **Universal Gateway** - Single endpoint that can proxy ANY external API
2. **API Key Vault** - Secure storage with automatic injection
3. **Service Registry** - Pre-configured common services
4. **Updated Prompts** - AI always uses gateway, never direct fetch

This is not a band-aid. This is the proper solution.

**Estimated implementation time: 4-6 hours**
**API key setup time for user: 15-20 minutes**



