# Faibric V3 Setup - API Keys Required

## What You Need To Do

Follow these steps in order. Total time: ~15-20 minutes.

---

## Step 1: Get Free API Keys (10-15 minutes)

### Required Keys (Do All of These)

| # | Service | Time | Link | What It Does |
|---|---------|------|------|--------------|
| 1 | **OpenWeather** | 2 min | [Sign Up](https://openweathermap.org/users/sign_up) | Weather data |
| 2 | **Alpha Vantage** | 1 min | [Get Key](https://www.alphavantage.co/support/#api-key) | Stock prices |
| 3 | **News API** | 2 min | [Register](https://newsapi.org/register) | News headlines |
| 4 | **Exchange Rate** | 1 min | [Sign Up](https://app.exchangerate-api.com/sign-up) | Currency rates |

### Optional Keys (Nice to Have)

| # | Service | Time | Link | What It Does |
|---|---------|------|------|--------------|
| 5 | Unsplash | 2 min | [Developers](https://unsplash.com/developers) | Stock photos |
| 6 | TMDB | 2 min | [API](https://www.themoviedb.org/settings/api) | Movie data |
| 7 | Giphy | 1 min | [Create App](https://developers.giphy.com/dashboard/?create=true) | GIFs |

---

## Step 2: Create Environment File (2 minutes)

### Option A: Create via Command Line

```bash
cd /Users/abram/Code/Faibric

cat > backend/.env << 'EOF'
# Core
OPENAI_API_KEY=sk-your-existing-openai-key

# Weather
OPENWEATHER_API_KEY=paste-key-here

# Stocks  
ALPHA_VANTAGE_API_KEY=paste-key-here

# News
NEWS_API_KEY=paste-key-here

# Currency
EXCHANGE_RATE_API_KEY=paste-key-here

# Optional
UNSPLASH_ACCESS_KEY=
TMDB_API_KEY=
GIPHY_API_KEY=
EOF
```

### Option B: Edit docker-compose.yml

Add to the `backend` service environment section:

```yaml
environment:
  - OPENWEATHER_API_KEY=your-key
  - ALPHA_VANTAGE_API_KEY=your-key
  - NEWS_API_KEY=your-key
  - EXCHANGE_RATE_API_KEY=your-key
```

---

## Step 3: Restart Services (1 minute)

```bash
cd /Users/abram/Code/Faibric
docker-compose down
docker-compose up -d
```

---

## Step 4: Test the Gateway

```bash
# Test weather
curl -X POST http://localhost:8000/api/gateway/ \
  -H "Content-Type: application/json" \
  -d '{"service": "openweather", "endpoint": "/weather", "params": {"q": "London"}}'

# Test stocks (free - no key needed!)
curl -X POST http://localhost:8000/api/gateway/ \
  -H "Content-Type: application/json" \
  -d '{"service": "yahoo_finance", "endpoint": "/chart/AAPL"}'

# Test crypto (free - no key needed!)
curl -X POST http://localhost:8000/api/gateway/ \
  -H "Content-Type: application/json" \
  -d '{"service": "coingecko", "endpoint": "/simple/price", "params": {"ids": "bitcoin", "vs_currencies": "usd"}}'
```

---

## How Each API Key Sign-up Works

### 1. OpenWeather (Weather Data)

1. Go to https://openweathermap.org/users/sign_up
2. Create account with email
3. Verify email
4. Go to https://home.openweathermap.org/api_keys
5. Copy the "Default" key or create a new one
6. **Note**: New keys take ~10 minutes to activate

### 2. Alpha Vantage (Stock Prices)

1. Go to https://www.alphavantage.co/support/#api-key
2. Fill out the simple form
3. Key appears immediately - copy it
4. **Note**: Limited to 5 calls/minute

### 3. News API (Headlines)

1. Go to https://newsapi.org/register
2. Create account
3. Verify email
4. Key shown on dashboard
5. **Note**: Free tier is development only (localhost)

### 4. Exchange Rate API (Currency)

1. Go to https://app.exchangerate-api.com/sign-up
2. Enter email
3. Get key instantly (no verification needed!)

---

## Services That Work Without Keys

These are already configured and work immediately:

| Service | What It Does | Example |
|---------|--------------|---------|
| `yahoo_finance` | Stock prices | `/chart/AAPL` |
| `coingecko` | Crypto prices | `/simple/price?ids=bitcoin` |
| `coindesk` | Bitcoin price | `/bpi/currentprice.json` |
| `restcountries` | Country data | `/all` |
| `jsonplaceholder` | Test data | `/posts` |

---

## After Setup: What Customers Can Build

With all keys configured, customers can ask for:

- "Create a weather dashboard for 5 cities"
- "Build a stock portfolio tracker"
- "Make a news aggregator"
- "Create a currency converter"
- "Build a crypto price tracker"
- "Make a recipe finder app"
- "Create a movie recommendation app"
- And much more...

**All without any manual intervention from you!**

---

## Troubleshooting

### "API key not configured" Error

The service requires a key you haven't set. Check:
1. Key is in environment/docker-compose
2. Docker services were restarted after adding key

### "Rate limit exceeded" Error

You've hit the free tier limit. Solutions:
1. Wait (limits reset hourly/daily)
2. Upgrade to paid tier
3. Use alternative service (e.g., yahoo_finance instead of alpha_vantage)

### Keys Not Working After Restart

```bash
# Check if keys are loaded
docker exec faibric_backend python -c "import os; print(os.environ.get('OPENWEATHER_API_KEY', 'NOT SET'))"
```

---

## Questions?

The gateway documentation is at:
- GET http://localhost:8000/api/gateway/ (lists all services)
- GET http://localhost:8000/api/gateway/services/ (service status)



