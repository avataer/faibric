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

IMPORTANT: Always use the FULL URL: https://api.faibric.com/api/gateway/

```javascript
// For pre-configured services (weather, stocks, news, etc.)
const response = await fetch('https://api.faibric.com/api/gateway/', {
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
        const res = await fetch('https://api.faibric.com/api/gateway/', {
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
2. Include ALL imports at the top
3. Export default the main component at the end
4. Make the UI beautiful and professional

## Available Libraries (USE THESE FOR BETTER APPS!)

You can import from these pre-installed libraries:
- react, react-dom (core)
- react-router-dom (for multi-page apps: BrowserRouter, Routes, Route, Link)
- recharts (for charts: LineChart, BarChart, PieChart, AreaChart, Line, Bar, XAxis, YAxis, etc.)
- lucide-react (for icons: Home, User, Settings, ArrowRight, TrendingUp, etc.)
- clsx (for conditional classNames)
- date-fns (for date formatting)

## Styling Options (BOTH WORK!)

1. TAILWIND CSS (RECOMMENDED for polished UIs):
   <div className="bg-gray-900 text-white p-6 rounded-xl shadow-lg hover:bg-gray-800 transition">

2. Inline styles (also works):
   <div style={{ backgroundColor: '#1a1a2e', padding: '20px' }}>

## Example: Professional Dashboard with Charts

```javascript
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Users } from 'lucide-react';

function App() {
  const [data] = useState([
    { name: 'Jan', value: 4000 },
    { name: 'Feb', value: 3000 },
    { name: 'Mar', value: 5000 },
  ]);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      {/* Stat Card */}
      <div className="bg-gray-800 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-400 text-sm">Total Revenue</p>
            <p className="text-3xl font-bold">$45,231</p>
          </div>
          <DollarSign className="w-8 h-8 text-blue-500" />
        </div>
      </div>
      
      {/* Chart */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h2 className="text-xl font-bold mb-4">Analytics</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none' }} />
            <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default App;
```

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

---

## Authentication (for apps that need login)

Faibric provides authentication via `window.FaibricAuth` (uses Supabase when configured, localStorage fallback otherwise):

```javascript
// Check if user is logged in
const isLoggedIn = window.FaibricAuth?.isLoggedIn();

// Get current user
const user = window.FaibricAuth?.getUser(); // { id, email, name } or null

// Sign up new user (async)
const user = await window.FaibricAuth?.signUp('user@example.com', 'password123');

// Login existing user (async)
const user = await window.FaibricAuth?.login('user@example.com', 'password123');

// Logout (async)
await window.FaibricAuth?.logout();

// Listen for auth state changes
window.FaibricAuth?.onAuthStateChange((event, session) => {
  console.log('Auth event:', event, session);
});
```

### Example: Protected SaaS App with Login/Signup

```javascript
import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LogIn, UserPlus, LogOut, Mail, Lock, Loader2 } from 'lucide-react';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // Check initial auth state
    const currentUser = window.FaibricAuth?.getUser();
    setUser(currentUser);
    setLoading(false);
    
    // Listen for auth changes
    const { data } = window.FaibricAuth?.onAuthStateChange((event, session) => {
      setUser(session?.user || null);
    }) || {};
    
    return () => data?.subscription?.unsubscribe?.();
  }, []);
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }
  
  if (!user) {
    return <AuthPage onAuth={(u) => setUser(u)} />;
  }
  
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950 text-white">
        <nav className="bg-gray-900 border-b border-gray-800 p-4 flex justify-between items-center">
          <span className="font-bold text-lg">MyApp</span>
          <div className="flex items-center gap-4">
            <span className="text-gray-400">{user.email}</span>
            <button 
              onClick={async () => { await window.FaibricAuth?.logout(); setUser(null); }}
              className="flex items-center gap-2 text-gray-400 hover:text-white"
            >
              <LogOut className="w-4 h-4" /> Logout
            </button>
          </div>
        </nav>
        <main className="p-6">
          <Routes>
            <Route path="/" element={<Dashboard user={user} />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

function AuthPage({ onAuth }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const user = isLogin 
        ? await window.FaibricAuth?.login(email, password)
        : await window.FaibricAuth?.signUp(email, password);
      onAuth(user);
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-white mb-2">
          {isLogin ? 'Welcome back' : 'Create account'}
        </h1>
        <p className="text-gray-400 mb-8">
          {isLogin ? 'Sign in to your account' : 'Sign up to get started'}
        </p>
        
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="Email"
              required
              className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Password"
              required
              minLength={6}
              className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-3 rounded-lg flex items-center justify-center gap-2 transition"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isLogin ? (
              <><LogIn className="w-5 h-5" /> Sign In</>
            ) : (
              <><UserPlus className="w-5 h-5" /> Create Account</>
            )}
          </button>
        </form>
        
        <p className="text-center text-gray-400 mt-6">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button 
            onClick={() => setIsLogin(!isLogin)} 
            className="text-blue-400 hover:text-blue-300"
          >
            {isLogin ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  );
}

function Dashboard({ user }) {
  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Welcome, {user.email?.split('@')[0]}!</h1>
      <p className="text-gray-400">Your dashboard content goes here.</p>
    </div>
  );
}

function Settings() {
  return <div className="max-w-4xl mx-auto"><h1 className="text-2xl font-bold">Settings</h1></div>;
}

export default App;
```

""" + GATEWAY_INSTRUCTIONS


# UI Polish directives - make apps look as good as Lovable
UI_POLISH = """
## MAKE IT BEAUTIFUL (Lovable-quality UI)

### Animations & Transitions (REQUIRED):
- Add hover states: hover:scale-105, hover:bg-gray-700, hover:shadow-xl
- Smooth transitions: transition-all duration-300
- Loading states: Use skeleton loaders or spinners with animate-pulse
- Entry animations: Add staggered fade-ins for lists

### Visual Polish:
- Shadows: shadow-lg, shadow-xl for depth
- Rounded corners: rounded-xl, rounded-2xl
- Gradients: bg-gradient-to-r from-blue-600 to-purple-600
- Blur effects: backdrop-blur-md for glass effects
- Icon badges: Colored circles behind icons

### Professional Details:
- Empty states with helpful messages and icons
- Proper spacing: gap-4, space-y-6, p-8
- Dividers between sections
- Subtle borders: border border-gray-700/50
- Focus rings: focus:ring-2 focus:ring-blue-500

### Color Schemes (pick ONE, be consistent):
1. Dark Pro: bg-gray-950 text-white with blue/purple accents
2. Light Clean: bg-white text-gray-900 with indigo accents  
3. Dark Blue: bg-slate-900 with cyan/teal accents
"""

# Condensed rules for faster generation
FAST_RULES = """
## CRITICAL: Understand The User's Request
- READ EVERY WORD of the request - the user is telling you EXACTLY what they want
- If they mention specific terms (e.g., "Livermore trade") - UNDERSTAND what it means and build around it
- If they mention specific items (e.g., "NBIS and CRWV stock") - use those EXACT items
- If they ask for N items (e.g., "10 moments") - generate EXACTLY N items
- DO NOT substitute generic content for specific requirements
- The user's request is your specification - follow it PRECISELY

## CRITICAL: REAL DATA vs FAKE DATA
- If user asks for "real data", "factual data", "historical data", "actual data" - you MUST fetch from APIs
- NEVER make up stock prices, dates, or financial data - USE THE GATEWAY
- For stocks: Use yahoo_finance service via Gateway to get REAL prices
- If you cannot fetch real data, TELL THE USER in the UI that live data requires API connection
- DO NOT HALLUCINATE financial data - it's dangerous and wrong

## Available Libraries (pre-installed):
- react, react-dom
- react-router-dom (BrowserRouter, Routes, Route, Link, useNavigate)
- recharts (LineChart, BarChart, PieChart, AreaChart, ResponsiveContainer, etc.)
- lucide-react (icons: Home, User, Settings, TrendingUp, Check, X, Plus, Search, Bell, etc.)
- clsx (conditional classNames)
- date-fns (date formatting)

## Styling: Tailwind CSS (className="bg-gray-900 text-white p-6")
- ALWAYS add transitions: transition-all duration-200
- ALWAYS add hover states: hover:bg-gray-700
- Use shadows for depth: shadow-lg shadow-xl
- Use rounded corners: rounded-xl rounded-2xl

## Auth: window.FaibricAuth?.login(email, pass) / logout() / getUser()

## Images: https://picsum.photos/seed/KEYWORD/800/600

## NO placeholder text, NO Lorem ipsum, generate REAL content!
"""


def get_generate_prompt(user_prompt: str) -> str:
    """Get optimized generation prompt with minimal but complete context."""
    
    # Detect what features are needed
    lower = user_prompt.lower()
    needs_routing = any(w in lower for w in ['pages', 'navigation', 'sidebar', 'menu', 'saas', 'dashboard', 'admin'])
    needs_charts = any(w in lower for w in ['chart', 'graph', 'analytics', 'dashboard', 'stats', 'metrics'])
    needs_auth = any(w in lower for w in ['login', 'signup', 'auth', 'user account', 'protected'])
    needs_api = any(w in lower for w in ['crypto', 'stock', 'weather', 'price', 'live', 'real-time', 'api'])
    needs_db = any(w in lower for w in ['save', 'store', 'persist', 'crud', 'todo', 'list', 'add', 'delete'])
    
    # Build context dynamically
    context_parts = [FAST_RULES]
    
    if needs_routing:
        context_parts.append("""
ROUTING: Use React Router
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
<BrowserRouter><Routes><Route path="/" element={<Home />} /></Routes></BrowserRouter>
""")
    
    if needs_charts:
        context_parts.append("""
CHARTS: Use Recharts
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer } from 'recharts';
<ResponsiveContainer width="100%" height={300}><LineChart data={data}><Line dataKey="value" stroke="#3b82f6" /></LineChart></ResponsiveContainer>
""")
    
    if needs_api:
        context_parts.append("""
EXTERNAL DATA: Use Faibric Gateway
await fetch('https://api.faibric.com/api/gateway/', { method: 'POST', body: JSON.stringify({ service: 'coingecko', endpoint: '/simple/price', params: { ids: 'bitcoin' } }) })
Services: coingecko (crypto), yahoo_finance (stocks), restcountries (countries)
""")
    
    if needs_db:
        context_parts.append("""
DATABASE: Use Faibric DB API
const APP_ID = window.FAIBRIC_APP_ID || 999;
fetch(`http://localhost:8000/api/v1/db/${APP_ID}/items/`, { method: 'POST', body: JSON.stringify({ data }) })
""")
    
    if needs_auth:
        context_parts.append("""
AUTH: Use FaibricAuth
const user = window.FaibricAuth?.getUser();
await window.FaibricAuth?.login(email, password);
await window.FaibricAuth?.logout();
""")
    
    # Check for trading/financial analysis
    needs_trading = any(w in lower for w in ['trade', 'trading', 'stock', 'livermore', 'earnings', 'buy', 'sell', 'profit', 'loss', 'backtest', 'factual', 'real data', 'historical'])
    if needs_trading:
        context_parts.append("""
TRADING/FINANCIAL DATA - USE REAL DATA:
- FETCH REAL stock data using the Gateway: 
  fetch('https://api.faibric.com/api/gateway/', {
    method: 'POST',
    body: JSON.stringify({ service: 'yahoo_finance', endpoint: '/chart/NBIS?range=1y&interval=1d' })
  })
- NEVER make up stock prices or dates - the user asked for FACTUAL data
- If user mentions specific stocks (NBIS, CRWV, etc.) - fetch their REAL data via yahoo_finance
- Show a loading state while fetching data
- If fetch fails, show: "Unable to load real-time data. Please check your connection."
- Calculate returns based on FETCHED data, not made-up numbers
- Use green for profits, red for losses
""")
    
    context = '\n'.join(context_parts)
    
    return f"""You are an expert React developer creating Lovable-quality apps. Build a complete, production-ready app.

USER REQUEST:
{user_prompt}

{context}

{UI_POLISH}

OUTPUT FORMAT (strict JSON only, no markdown):
{{
    "app_type": "website|dashboard|tool|game|other",
    "title": "App Title",
    "description": "Brief description",
    "api_services": [],
    "components": {{
        "App": "// Complete App.jsx with imports and export default App;"
    }}
}}

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON - no markdown, no explanations
2. Use Tailwind CSS for ALL styling (className="...")
3. ADD ANIMATIONS: transition-all duration-300, hover states on every interactive element
4. Use Lucide icons generously for visual polish
5. Use Recharts for any charts/graphs with proper styling
6. Dark theme by default: bg-gray-950/bg-slate-900 backgrounds
7. NO placeholder text - write REAL, specific content
8. Include loading states and empty states
9. Make hover effects obvious and satisfying

STOCK/FINANCIAL DATA REQUIREMENT:
If the user asks for stock data, trading analysis, or financial data:
- You MUST use useEffect to fetch REAL data from: https://api.faibric.com/api/gateway/
- Example: fetch('https://api.faibric.com/api/gateway/', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{service:'yahoo_finance', endpoint:'/chart/NBIS?range=1y&interval=1d'}})}})
- Parse result.data for actual prices
- NEVER hardcode stock prices - they will be WRONG
- Show loading state while fetching
- If you cannot fetch, display: "Loading real market data..."

Generate beautiful, polished code now:"""


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
const res = await fetch('https://api.faibric.com/api/gateway/', {
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
const res = await fetch('https://api.faibric.com/api/gateway/', {
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

STRIPE_HINT = """
## IMPORTANT: For PAYMENT/CHECKOUT/SUBSCRIPTION apps, use this Stripe template:

Faibric apps can integrate Stripe for payments. Here's how:

### Pricing Page with Checkout:
```javascript
import React, { useState } from 'react';
import { Check, Zap, Crown, Sparkles } from 'lucide-react';

function App() {
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const plans = [
    {
      id: 'starter',
      name: 'Starter',
      price: 9,
      features: ['5 Projects', 'Basic Analytics', 'Email Support'],
      popular: false,
    },
    {
      id: 'pro',
      name: 'Pro',
      price: 29,
      features: ['Unlimited Projects', 'Advanced Analytics', 'Priority Support', 'API Access'],
      popular: true,
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 99,
      features: ['Everything in Pro', 'Custom Integrations', 'Dedicated Manager', 'SLA'],
      popular: false,
    },
  ];
  
  const handleCheckout = async (planId) => {
    setLoading(true);
    // In production, this would call your backend to create a Stripe checkout session
    // For demo, we'll show the flow
    alert(`Redirecting to Stripe checkout for ${planId} plan...`);
    setLoading(false);
  };
  
  return (
    <div className="min-h-screen bg-gray-900 py-20 px-4">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-white text-center mb-4">Simple, Transparent Pricing</h1>
        <p className="text-gray-400 text-center mb-12">Choose the plan that's right for you</p>
        
        <div className="grid md:grid-cols-3 gap-8">
          {plans.map(plan => (
            <div key={plan.id} className={`relative bg-gray-800 rounded-2xl p-8 ${plan.popular ? 'ring-2 ring-blue-500' : ''}`}>
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-blue-500 text-white px-4 py-1 rounded-full text-sm font-medium">
                  Most Popular
                </div>
              )}
              <h3 className="text-xl font-bold text-white">{plan.name}</h3>
              <div className="mt-4 flex items-baseline">
                <span className="text-5xl font-bold text-white">${plan.price}</span>
                <span className="text-gray-400 ml-2">/month</span>
              </div>
              <ul className="mt-8 space-y-4">
                {plan.features.map(feature => (
                  <li key={feature} className="flex items-center text-gray-300">
                    <Check className="w-5 h-5 text-green-400 mr-3" />
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleCheckout(plan.id)}
                disabled={loading}
                className={`mt-8 w-full py-3 rounded-lg font-medium transition ${
                  plan.popular 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-gray-700 text-white hover:bg-gray-600'
                }`}
              >
                {loading ? 'Processing...' : 'Get Started'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
```

ALWAYS create beautiful pricing pages with clear CTAs and feature lists!
"""

SAAS_HINT = """
## IMPORTANT: For SAAS/ADMIN DASHBOARD apps, use this structure:

### Multi-page SaaS with Sidebar:
```javascript
import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Home, BarChart2, Users, Settings, LogOut, Menu, X, Bell, Search } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function Sidebar({ isOpen, setIsOpen }) {
  const location = useLocation();
  const links = [
    { to: '/', icon: Home, label: 'Dashboard' },
    { to: '/analytics', icon: BarChart2, label: 'Analytics' },
    { to: '/users', icon: Users, label: 'Users' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];
  
  return (
    <aside className={`fixed left-0 top-0 h-full bg-gray-900 border-r border-gray-800 transition-all z-50 ${isOpen ? 'w-64' : 'w-20'}`}>
      <div className="p-4 flex items-center justify-between">
        {isOpen && <span className="text-xl font-bold text-white">AppName</span>}
        <button onClick={() => setIsOpen(!isOpen)} className="text-gray-400 hover:text-white p-2">
          {isOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      <nav className="mt-8 px-2">
        {links.map(link => (
          <Link
            key={link.to}
            to={link.to}
            className={`flex items-center px-4 py-3 rounded-lg mb-1 transition ${
              location.pathname === link.to 
                ? 'bg-blue-600 text-white' 
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <link.icon size={20} />
            {isOpen && <span className="ml-3">{link.label}</span>}
          </Link>
        ))}
      </nav>
    </aside>
  );
}

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-950">
        <Sidebar isOpen={sidebarOpen} setIsOpen={setSidebarOpen} />
        <main className={`transition-all ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
          {/* Header */}
          <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center">
              <Search className="w-5 h-5 text-gray-400" />
              <input className="bg-transparent border-none text-white ml-3 focus:outline-none" placeholder="Search..." />
            </div>
            <div className="flex items-center gap-4">
              <button className="text-gray-400 hover:text-white"><Bell size={20} /></button>
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">U</div>
            </div>
          </header>
          
          {/* Content */}
          <div className="p-6">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/users" element={<UsersPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
```

ALWAYS create polished SaaS apps with proper navigation, headers, and page routing!
"""

ECOMMERCE_HINT = """
## IMPORTANT: For E-COMMERCE / PRODUCT apps, use this structure:

```javascript
import React, { useState } from 'react';
import { ShoppingCart, Heart, Star, Plus, Minus, X, ChevronLeft, ChevronRight } from 'lucide-react';

function App() {
  const [cart, setCart] = useState([]);
  const [showCart, setShowCart] = useState(false);
  
  const products = [
    { id: 1, name: 'Premium Wireless Headphones', price: 299, rating: 4.8, reviews: 124, image: 'https://picsum.photos/seed/headphones1/400/400', category: 'Electronics' },
    { id: 2, name: 'Minimalist Watch', price: 189, rating: 4.9, reviews: 89, image: 'https://picsum.photos/seed/watch1/400/400', category: 'Accessories' },
    { id: 3, name: 'Leather Messenger Bag', price: 149, rating: 4.7, reviews: 56, image: 'https://picsum.photos/seed/bag1/400/400', category: 'Bags' },
  ];
  
  const addToCart = (product) => {
    const existing = cart.find(item => item.id === product.id);
    if (existing) {
      setCart(cart.map(item => item.id === product.id ? {...item, quantity: item.quantity + 1} : item));
    } else {
      setCart([...cart, {...product, quantity: 1}]);
    }
  };
  
  const cartTotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex justify-between items-center sticky top-0 z-40">
        <h1 className="text-xl font-bold">Store</h1>
        <button onClick={() => setShowCart(true)} className="relative">
          <ShoppingCart className="w-6 h-6" />
          {cart.length > 0 && (
            <span className="absolute -top-2 -right-2 bg-blue-600 text-xs w-5 h-5 rounded-full flex items-center justify-center">
              {cart.reduce((sum, item) => sum + item.quantity, 0)}
            </span>
          )}
        </button>
      </header>
      
      {/* Products Grid */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map(product => (
            <div key={product.id} className="bg-gray-900 rounded-xl overflow-hidden border border-gray-800 hover:border-gray-700 transition">
              <div className="aspect-square relative">
                <img src={product.image} alt={product.name} className="w-full h-full object-cover" />
                <button className="absolute top-3 right-3 p-2 bg-gray-900/80 rounded-full hover:bg-gray-800">
                  <Heart className="w-5 h-5" />
                </button>
              </div>
              <div className="p-4">
                <h3 className="font-semibold mb-1">{product.name}</h3>
                <div className="flex items-center gap-2 mb-3">
                  <Star className="w-4 h-4 text-yellow-400 fill-current" />
                  <span className="text-sm text-gray-400">{product.rating} ({product.reviews} reviews)</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xl font-bold">${product.price}</span>
                  <button onClick={() => addToCart(product)} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium transition">
                    Add to Cart
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
      
      {/* Cart Sidebar */}
      {showCart && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowCart(false)} />
          <div className="relative w-full max-w-md bg-gray-900 h-full p-6 overflow-auto">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold">Cart ({cart.length})</h2>
              <button onClick={() => setShowCart(false)}><X className="w-6 h-6" /></button>
            </div>
            {cart.map(item => (
              <div key={item.id} className="flex gap-4 py-4 border-b border-gray-800">
                <img src={item.image} className="w-20 h-20 rounded object-cover" />
                <div className="flex-1">
                  <h3 className="font-medium">{item.name}</h3>
                  <p className="text-gray-400">${item.price} x {item.quantity}</p>
                </div>
              </div>
            ))}
            <div className="mt-6 pt-6 border-t border-gray-800">
              <div className="flex justify-between text-xl font-bold mb-4">
                <span>Total</span>
                <span>${cartTotal}</span>
              </div>
              <button className="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-medium">
                Checkout
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
```

ALWAYS create polished e-commerce with product cards, cart functionality, and smooth interactions!
"""

LANDING_HINT = """
## IMPORTANT: For LANDING PAGE / MARKETING apps, use this structure:

```javascript
import React, { useState } from 'react';
import { ArrowRight, Check, Star, Zap, Shield, Clock, ChevronDown } from 'lucide-react';

function App() {
  const [email, setEmail] = useState('');
  
  const features = [
    { icon: Zap, title: 'Lightning Fast', description: 'Built for speed with optimized performance' },
    { icon: Shield, title: 'Enterprise Security', description: 'Bank-grade encryption and security' },
    { icon: Clock, title: '24/7 Support', description: 'Round-the-clock customer assistance' },
  ];
  
  const testimonials = [
    { name: 'Sarah Chen', role: 'CEO, TechCorp', text: 'This product transformed our business. Absolutely incredible.', avatar: 'https://picsum.photos/seed/avatar1/100/100' },
    { name: 'James Wilson', role: 'Founder, StartupXYZ', text: 'Best investment we ever made. The ROI speaks for itself.', avatar: 'https://picsum.photos/seed/avatar2/100/100' },
  ];
  
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Hero Section */}
      <header className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-purple-600/10 to-transparent" />
        <nav className="relative max-w-7xl mx-auto px-6 py-6 flex justify-between items-center">
          <span className="text-2xl font-bold">Brand</span>
          <div className="hidden md:flex gap-8">
            <a href="#features" className="text-gray-400 hover:text-white transition">Features</a>
            <a href="#pricing" className="text-gray-400 hover:text-white transition">Pricing</a>
            <a href="#testimonials" className="text-gray-400 hover:text-white transition">Testimonials</a>
          </div>
          <button className="bg-blue-600 hover:bg-blue-700 px-5 py-2 rounded-lg font-medium transition">
            Get Started
          </button>
        </nav>
        
        <div className="relative max-w-7xl mx-auto px-6 py-24 text-center">
          <div className="inline-flex items-center gap-2 bg-blue-600/10 border border-blue-600/30 rounded-full px-4 py-1.5 mb-6">
            <Zap className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-blue-400">Now with AI-powered features</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            Build Something<br />
            <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              Amazing Today
            </span>
          </h1>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-8">
            The all-in-one platform that helps you create, launch, and scale your business faster than ever before.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              className="px-5 py-3 rounded-lg bg-gray-900 border border-gray-800 focus:border-blue-600 focus:outline-none w-full sm:w-80"
            />
            <button className="bg-blue-600 hover:bg-blue-700 px-8 py-3 rounded-lg font-medium flex items-center justify-center gap-2 transition">
              Start Free Trial <ArrowRight className="w-5 h-5" />
            </button>
          </div>
          <p className="text-gray-500 text-sm mt-4">No credit card required • 14-day free trial</p>
        </div>
      </header>
      
      {/* Features */}
      <section id="features" className="max-w-7xl mx-auto px-6 py-24">
        <h2 className="text-3xl font-bold text-center mb-4">Why Choose Us</h2>
        <p className="text-gray-400 text-center mb-16 max-w-2xl mx-auto">Everything you need to succeed</p>
        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, i) => (
            <div key={i} className="bg-gray-900 border border-gray-800 rounded-2xl p-8 hover:border-gray-700 transition">
              <div className="w-12 h-12 bg-blue-600/10 rounded-xl flex items-center justify-center mb-4">
                <feature.icon className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
              <p className="text-gray-400">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>
      
      {/* Testimonials */}
      <section id="testimonials" className="bg-gray-900 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center mb-16">Loved by Thousands</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {testimonials.map((t, i) => (
              <div key={i} className="bg-gray-950 border border-gray-800 rounded-2xl p-8">
                <div className="flex gap-1 mb-4">
                  {[...Array(5)].map((_, i) => <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />)}
                </div>
                <p className="text-lg mb-6">"{t.text}"</p>
                <div className="flex items-center gap-3">
                  <img src={t.avatar} className="w-12 h-12 rounded-full" />
                  <div>
                    <div className="font-medium">{t.name}</div>
                    <div className="text-sm text-gray-400">{t.role}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
      
      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 py-24 text-center">
        <h2 className="text-4xl font-bold mb-4">Ready to Get Started?</h2>
        <p className="text-gray-400 mb-8">Join thousands of happy customers today.</p>
        <button className="bg-blue-600 hover:bg-blue-700 px-8 py-4 rounded-lg font-medium text-lg transition">
          Start Your Free Trial
        </button>
      </section>
    </div>
  );
}

export default App;
```

ALWAYS create stunning landing pages with hero section, features, testimonials, and CTAs!
"""


def get_prompt_for_request(user_prompt: str) -> str:
    """Get the appropriate prompt with hints based on user request"""
    prompt = get_generate_prompt(user_prompt)
    
    # Add relevant hints based on request type
    lower = user_prompt.lower()
    
    # Crypto apps
    if any(w in lower for w in ['crypto', 'bitcoin', 'ethereum', 'coin', 'blockchain']):
        prompt += "\n\nHINT FOR THIS REQUEST:" + CRYPTO_HINT
    
    # Investment tracking gets special hint
    if any(w in lower for w in ['invest', 'portfolio', 'bought', 'purchased', 'return', 'profit', 'loss', 'what is it worth', "what's it worth"]):
        prompt += "\n\nCRITICAL HINT FOR THIS REQUEST:" + INVESTMENT_HINT
    elif any(w in lower for w in ['stock', 'market', 'trading', 'finance', 'price']):
        prompt += "\n\nHINT FOR THIS REQUEST:" + STOCK_HINT
    
    # Payment/pricing apps
    if any(w in lower for w in ['pricing', 'payment', 'checkout', 'subscription', 'stripe', 'pay', 'billing', 'plan']):
        prompt += "\n\nHINT FOR THIS REQUEST:" + STRIPE_HINT
    
    # SaaS/Dashboard apps
    if any(w in lower for w in ['saas', 'admin', 'dashboard', 'panel', 'crm', 'erp', 'management system', 'sidebar']):
        prompt += "\n\nHINT FOR THIS REQUEST:" + SAAS_HINT
    
    # E-commerce apps
    if any(w in lower for w in ['ecommerce', 'e-commerce', 'shop', 'store', 'product', 'cart', 'catalog', 'marketplace']):
        prompt += "\n\nHINT FOR THIS REQUEST:" + ECOMMERCE_HINT
    
    # Landing pages
    if any(w in lower for w in ['landing', 'marketing', 'hero', 'waitlist', 'coming soon', 'launch', 'startup', 'saas landing']):
        prompt += "\n\nHINT FOR THIS REQUEST:" + LANDING_HINT
    
    return prompt
