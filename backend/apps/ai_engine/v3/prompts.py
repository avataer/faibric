"""
V3 AI Prompts - Universal Architecture
All generated apps use the Faibric Gateway for external data
"""

# Gateway usage instructions - included in ALL prompts
GATEWAY_INSTRUCTIONS = """
## CRITICAL: External Data Access

NEVER use fetch() to call external APIs directly - browsers block CORS.
ALWAYS use the Faibric Gateway at /api/gateway/

### How to use the Gateway:

IMPORTANT: Always use the FULL URL: http://localhost:8000/api/gateway/

```javascript
// For pre-configured services (weather, stocks, news, etc.)
const response = await fetch('http://localhost:8000/api/gateway/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    service: 'SERVICE_NAME',
    endpoint: '/endpoint',
    params: { key: 'value' }
  })
});
const result = await response.json();
const actualData = result.data;  // The actual API response is in result.data
```

### Available Services (FREE - no API key needed):

| Service | ID | Example endpoint | Returns |
|---------|-----|-----------------|---------|
| Stocks | yahoo_finance | /chart/AAPL | Stock data |
| Crypto | coingecko | /simple/price?ids=bitcoin&vs_currencies=usd | Crypto prices |
| Countries | restcountries | /all | Country data |

### Example: Crypto Price Tracker (FREE)

```javascript
import React, { useState, useEffect } from 'react';

function App() {
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPrices = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/gateway/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            service: 'coingecko',
            endpoint: '/simple/price',
            params: { ids: 'bitcoin,ethereum,solana', vs_currencies: 'usd', include_24hr_change: 'true' }
          })
        });
        const result = await res.json();
        if (result.success) {
          setPrices(result.data);
        }
        setLoading(false);
      } catch (err) {
        console.error(err);
        setLoading(false);
      }
    };
    fetchPrices();
    const interval = setInterval(fetchPrices, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div style={{ padding: '20px', background: '#1a1a2e', minHeight: '100vh', color: 'white' }}>
      <h1>Crypto Prices</h1>
      {Object.entries(prices).map(([coin, data]) => (
        <div key={coin} style={{ margin: '20px 0', padding: '15px', background: '#16213e', borderRadius: '8px' }}>
          <h2>{coin.toUpperCase()}: ${data.usd?.toLocaleString()}</h2>
          <p style={{ color: data.usd_24h_change > 0 ? '#00ff88' : '#ff4444' }}>
            24h Change: {data.usd_24h_change?.toFixed(2)}
          </p>
        </div>
      ))}
    </div>
  );
}

export default App;
```

IMPORTANT:
1. ALWAYS use the gateway - direct API calls will fail
2. Handle loading and error states
3. The gateway returns { success: bool, data: ... }
4. PREFER free services (coingecko, yahoo_finance, restcountries)
"""

# Base rules for all generated code
BASE_RULES = """
## Code Rules

1. Use React with hooks (useState, useEffect, etc.)
2. Use ONLY inline styles - no external CSS files
3. Include ALL imports at the top: import React, { useState, useEffect } from 'react';
4. Export default the main component at the end
5. Make the UI beautiful and professional

## CRITICAL: Content Classification Rules

### TYPE 1: STATIC CONTENT (product lists, info pages, recipes, descriptions, catalogs)
**ALWAYS generate as hardcoded JavaScript data in the code!**

Example - Product Catalog:
```javascript
const products = [
  { id: 1, name: 'Vintage Pickup', description: 'Classic 50s tone with alnico magnets...' },
  { id: 2, name: 'Hot Rails', description: 'High-output humbucker in single-coil size...' },
];
// Then render: products.map(p => <div key={p.id}>{p.name}</div>)
```

NEVER use database API for static info like:
- Product catalogs
- Company info / About pages  
- Recipe lists
- Movie/book databases
- Any pre-defined content

### TYPE 2: USER-GENERATED CONTENT (posts, comments, todos, form submissions)
Use the Faibric Database API - users will add/edit/delete this data.

### TYPE 3: REAL-TIME DATA (stocks, weather, crypto, live feeds)
Use the Faibric Gateway API - data changes frequently.

---

## Faibric Database API (ONLY for user-generated content)

### Faibric Database API (ALWAYS use this for data storage)

Base URL: http://localhost:8000/api/v1/db/APP_ID/COLLECTION_NAME/

Replace APP_ID with the app's project ID (injected as window.FAIBRIC_APP_ID).

```javascript
const APP_ID = window.FAIBRIC_APP_ID || 999;  // Fallback for testing
const API_BASE = 'http://localhost:8000/api/v1/db/' + APP_ID;

// CREATE - Add new item
const createItem = async (collection, data) => {
  const res = await fetch(API_BASE + '/' + collection + '/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  });
  return await res.json();
};

// READ - Get all items
const getItems = async (collection) => {
  const res = await fetch(API_BASE + '/' + collection + '/');
  const result = await res.json();
  return result.documents || [];
};

// UPDATE - Update an item
const updateItem = async (collection, id, data) => {
  const res = await fetch(API_BASE + '/' + collection + '/' + id + '/', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  });
  return await res.json();
};

// DELETE - Delete an item
const deleteItem = async (collection, id) => {
  await fetch(API_BASE + '/' + collection + '/' + id + '/', { method: 'DELETE' });
};
```

### Complete Example - News App:

```javascript
import React, { useState, useEffect } from 'react';

function App() {
  const [news, setNews] = useState([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);
  
  const APP_ID = window.FAIBRIC_APP_ID || 999;
  const API = 'http://localhost:8000/api/v1/db/' + APP_ID + '/news';

  // Load news on mount
  useEffect(() => {
    fetch(API + '/')
      .then(r => r.json())
      .then(data => {
        setNews(data.documents || []);
        setLoading(false);
      });
  }, []);

  // Add news
  const addNews = async () => {
    if (!text.trim()) return;
    const res = await fetch(API + '/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: { text, date: new Date().toISOString() } })
    });
    const result = await res.json();
    setNews([{ id: result.id, data: { text, date: new Date().toISOString() } }, ...news]);
    setText('');
  };

  // Delete news
  const deleteNews = async (id) => {
    await fetch(API + '/' + id + '/', { method: 'DELETE' });
    setNews(news.filter(n => n.id !== id));
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div style={{ padding: '20px' }}>
      <h1>News</h1>
      <input value={text} onChange={e => setText(e.target.value)} />
      <button onClick={addNews}>Add</button>
      {news.map(n => (
        <div key={n.id}>
          <p>{n.data.text}</p>
          <button onClick={() => deleteNews(n.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}

export default App;
```

IMPORTANT:
- ALWAYS use the Faibric Database API for data that needs to persist
- Data is stored in the cloud, accessible by ALL users of the app
- Each app has isolated data (by APP_ID)

""" + GATEWAY_INSTRUCTIONS


def get_generate_prompt(user_prompt: str) -> str:
    """Get generation prompt with user prompt inserted"""
    return f"""You are an expert React developer building apps for the Faibric platform.

USER REQUEST:
{user_prompt}

{BASE_RULES}

OUTPUT FORMAT (strict JSON - MUST be valid JSON):
{{
    "app_type": "website|dashboard|tool|game|other",
    "title": "App Title",
    "description": "Brief description",
    "api_services": ["list", "of", "services", "used"],
    "components": {{
        "App": "// Complete App.tsx code with imports and export default"
    }}
}}

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON - no markdown, no backticks
2. The "App" component must be complete and runnable
3. MUST include: import React, {{ useState, useEffect }} from 'react';
4. MUST include: export default App; at the end
5. For STATIC CONTENT (product lists, catalogs, info pages): 
   - HARDCODE the data as JavaScript arrays/objects in the code
   - DO NOT use database API for static content!
   - Include REAL descriptions, not placeholders
6. For USER-GENERATED content (posts, todos): Use Database API
7. For REAL-TIME data (stocks, crypto): Use Gateway API
8. Make it visually stunning with proper inline styles

Generate now:"""


def get_modify_prompt(current_code: str, user_request: str) -> str:
    """Get modification prompt with code and request inserted"""
    # Check if investment-related
    lower = user_request.lower()
    investment_hint = ""
    if any(w in lower for w in ['invest', 'portfolio', 'bought', 'purchased', 'return', 'profit', 'worth', '$', '10000', '10,000']):
        investment_hint = "\n\n" + INVESTMENT_HINT
    
    return f"""You are modifying a React app for the Faibric platform.

IMPORTANT: The user's message might be:
1. A request for changes (e.g., "add a dark mode") - Make the requested changes
2. Feedback about a problem (e.g., "i see no data", "it's broken") - Fix the existing app, don't replace it
3. Confusion about what they see - Keep the current app's purpose, just fix any issues

If the user seems confused or reports an error, DO NOT completely replace the app with something different.
Instead, fix the current app to work better.

CURRENT CODE:
{current_code}

USER REQUEST:
{user_request}

{BASE_RULES}{investment_hint}

CRITICAL RULES:
1. Return ONLY the complete modified code - no JSON wrapper, no markdown, no backticks
2. If user asks for STATIC CONTENT (product lists, info pages, catalogs):
   - HARDCODE all the data as JavaScript arrays/objects
   - Include REAL, detailed descriptions - NO placeholders
   - DO NOT use database API for static content!
3. If user asks for USER-GENERATED content (posts, todos, forms): Use Database API
4. If user asks for REAL-TIME data (stocks, crypto): Use Gateway API
5. MUST start with: import React...
6. MUST end with: export default App;
7. For investment tracking - USE the investment service

Return the complete modified component code:"""


def get_analyze_prompt(user_prompt: str) -> str:
    """Get analysis prompt with user prompt inserted"""
    return f"""Analyze this user request and determine what kind of app they want.

USER REQUEST:
{user_prompt}

Respond with JSON only:
{{
    "app_type": "website|dashboard|tool|game|ecommerce|social|other",
    "complexity": "simple|medium|complex",
    "needs_backend": false,
    "needs_database": false,
    "needs_auth": false,
    "external_apis": ["list of APIs needed"],
    "suggested_services": ["coingecko", "yahoo_finance", "restcountries"],
    "key_features": ["list of main features"],
    "styling": "dark|light|colorful|minimal"
}}

Prefer free services (coingecko, yahoo_finance, restcountries) when possible."""


# Service-specific hints
CRYPTO_HINT = """
For crypto prices, use CoinGecko (FREE, no key needed):
service: 'coingecko'
endpoint: '/simple/price'
params: { ids: 'bitcoin,ethereum,solana', vs_currencies: 'usd', include_24hr_change: 'true' }
Response: result.data = { bitcoin: { usd: 97000, usd_24h_change: 2.5 }, ... }
"""

STOCK_HINT = """
For stocks, use Yahoo Finance (FREE, no key needed):
service: 'yahoo_finance'
endpoint: '/chart/AAPL'  (or /chart/GOOGL, /chart/MSFT, etc.)
Response: result.data.chart.result[0].meta.regularMarketPrice = 275.92
"""

INVESTMENT_HINT = """
## IMPORTANT: For INVESTMENT TRACKING/PORTFOLIO apps, use the Investment Service:

This service automatically calculates investment returns with REAL data!

### Single Stock Investment:
```javascript
const res = await fetch('http://localhost:8000/api/gateway/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    service: 'investment',
    symbol: 'AAPL',      // Stock ticker
    amount: 10000,       // Amount invested in USD
    start_date: '2024-01-02'  // When you bought
  })
});
const { data } = await res.json();
// data = {
//   symbol: 'AAPL',
//   invested_amount: 10000,
//   shares_owned: 52.08,
//   start_price: 192.00,
//   start_date: '2024-01-02',
//   end_price: 228.50,
//   end_date: '2024-11-25',
//   current_value: 11900.00,
//   profit_loss: 1900.00,
//   percent_change: 19.00
// }
```

### Portfolio (Multiple Stocks):
```javascript
const res = await fetch('http://localhost:8000/api/gateway/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    service: 'investment',
    portfolio: [
      { symbol: 'AAPL', amount: 3333, start_date: '2024-01-02' },
      { symbol: 'TSLA', amount: 3333, start_date: '2024-01-02' },
      { symbol: 'ASML', amount: 3334, start_date: '2024-01-02' }
    ]
  })
});
const { data } = await res.json();
// data = {
//   stocks: [ individual results... ],
//   total_invested: 10000,
//   total_current_value: 12500,
//   total_profit_loss: 2500,
//   total_percent_change: 25.00
// }
```

ALWAYS use this service for investment tracking - it does all the calculations correctly!
"""


def get_prompt_for_request(user_prompt: str) -> str:
    """Get the appropriate prompt with hints based on user request"""
    prompt = get_generate_prompt(user_prompt)
    
    # Add relevant hints
    lower = user_prompt.lower()
    if any(w in lower for w in ['crypto', 'bitcoin', 'ethereum', 'coin', 'blockchain']):
        prompt += "\n\nHINT FOR THIS REQUEST:" + CRYPTO_HINT
    
    # Investment tracking gets special hint
    if any(w in lower for w in ['invest', 'portfolio', 'bought', 'purchased', 'return', 'profit', 'loss', 'what is it worth', "what's it worth"]):
        prompt += "\n\nCRITICAL HINT FOR THIS REQUEST:" + INVESTMENT_HINT
    elif any(w in lower for w in ['stock', 'market', 'trading', 'finance', 'price']):
        prompt += "\n\nHINT FOR THIS REQUEST:" + STOCK_HINT
    
    return prompt
