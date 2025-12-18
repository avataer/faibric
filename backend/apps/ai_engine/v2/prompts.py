"""
V2 System Prompts - Specialized, single-shot generation
These prompts are sent to OpenAI's API to generate code.
"""

# Classification prompt to determine what type of app to build
CLASSIFY_PROMPT = """Classify this request into ONE category:
- website: Static content site (portfolio, landing page, info site)
- tool: Interactive tool (calculator, converter, counter, timer, generator)
- dashboard: Data display with charts/metrics/stats
- form: Data collection form
- game: Interactive game

Request: "{prompt}"

Reply with ONLY the category name, nothing else."""


# BASE RULES that apply to ALL prompts
BASE_RULES = """
ABSOLUTE RULES (NEVER BREAK THESE):
1. Output ONLY valid JSON - no markdown, no backticks, no explanations
2. Use ONLY inline styles: style={{{{ backgroundColor: '#000' }}}}
3. NEVER use fetch(), axios, or any HTTP requests - browsers block CORS
4. ALL data must be defined inside the component using useState
5. For "live" data: use useEffect + setInterval to randomly update values
6. Import ONLY from 'react': import React, {{ useState, useEffect }} from 'react'
7. NO external libraries, NO imports except React
8. Component must be a complete, working, self-contained function
9. TYPOGRAPHY: ALWAYS use Apple San Francisco font. Set on EVERY text element:
   fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif"
   This is MANDATORY - NEVER use any other font unless user explicitly requests it.

CONTENT RULES (EXTREMELY IMPORTANT):
- NEVER use placeholder text: No "Lorem ipsum", "placeholder", "[Your text]", "Coming soon", "Sample", "Example"
- NEVER use placeholder images: No "placeholder.jpg", "example.png", empty src, or via.placeholder.com
- Generate REAL, realistic content that matches the business/site type
- Write compelling, professional copy as if for a real business
- Include realistic prices, names, descriptions, testimonials

IMAGE RULES (CRITICAL - FOLLOW EXACTLY):
- Use Picsum for placeholder images: https://picsum.photos/seed/KEYWORD/800/600
- Replace KEYWORD with a relevant word (e.g., dog1, portrait2, art3)
- Each image should have a UNIQUE seed to get different images
- Example: https://picsum.photos/seed/asian-woman-dogs-1/800/600
- For variety, increment the number: seed/dog1, seed/dog2, seed/dog3
- These URLs always work and return real photos
- NEVER use source.unsplash.com - it is broken
- NEVER leave image src empty or use placeholder.jpg
"""


# Single-shot website generator
WEBSITE_PROMPT = """You are an expert React developer. Create a complete, production-ready website.

USER REQUEST:
{user_prompt}

""" + BASE_RULES + """

WEBSITE-SPECIFIC RULES:
1. Generate REAL content - not "Lorem ipsum" or placeholders
2. Make it visually stunning with gradients, shadows, proper spacing
3. Include all sections the user asks for
4. Use a cohesive color scheme

OUTPUT FORMAT (strict JSON):
{{
    "title": "Page Title",
    "components": {{
        "App": "import React from 'react';\\n\\nfunction App() {{\\n  return (\\n    <div style={{{{ minHeight: '100vh' }}}}>\\n      // content here\\n    </div>\\n  );\\n}}\\n\\nexport default App;"
    }}
}}

Generate now:"""


# Single-shot tool generator
TOOL_PROMPT = """You are an expert React developer. Create a fully functional interactive tool.

USER REQUEST:
{user_prompt}

""" + BASE_RULES + """

TOOL-SPECIFIC RULES:
1. Tool must be 100% FUNCTIONAL with real calculations/logic
2. Include proper input validation and user feedback
3. Beautiful, modern UI with good UX
4. Use useState for all interactive state

OUTPUT FORMAT (strict JSON):
{{
    "title": "Tool Name",
    "components": {{
        "App": "import React, {{ useState }} from 'react';\\n\\nfunction App() {{\\n  const [value, setValue] = useState(0);\\n  // tool logic here\\n  return <div>...</div>;\\n}}\\n\\nexport default App;"
    }}
}}

Generate now:"""


# Single-shot dashboard generator  
DASHBOARD_PROMPT = """You are an expert React developer. Create a data dashboard with live-updating data.

USER REQUEST:
{user_prompt}

""" + BASE_RULES + """

DASHBOARD-SPECIFIC RULES:
1. NEVER use fetch() or any external API calls - they will fail due to CORS
2. Generate REALISTIC stock data as initial state in useState
3. Use useEffect + setInterval to simulate live updates (random price changes every 2-5 seconds)
4. Show green for positive change, red for negative
5. Include realistic price ranges for each stock (AAPL ~150-200, NVDA ~400-500, etc.)
6. Create mini charts using colored DIVs as bar charts showing price history
7. Dark theme preferred: background #0f0f0f or #1a1a2e
8. Display current time/date, market status (OPEN/CLOSED based on time)

EXAMPLE PATTERN FOR LIVE STOCK DASHBOARD:
import React, {{ useState, useEffect }} from 'react';

function App() {{
  const [stocks, setStocks] = useState([
    {{ symbol: 'AAPL', price: 178.52, change: 2.34, changePercent: 1.33, volume: 52340000, history: [175, 176, 177, 178, 178.52] }},
    {{ symbol: 'NVDA', price: 467.23, change: 12.45, changePercent: 2.74, volume: 41200000, history: [455, 458, 462, 465, 467.23] }},
    {{ symbol: 'TSLA', price: 251.80, change: -3.20, changePercent: -1.25, volume: 89100000, history: [255, 254, 253, 252, 251.80] }},
  ]);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {{
    const interval = setInterval(() => {{
      setStocks(prev => prev.map(stock => {{
        const change = (Math.random() - 0.5) * 2;
        const newPrice = Math.max(1, stock.price + change);
        return {{
          ...stock,
          price: Math.round(newPrice * 100) / 100,
          change: Math.round(change * 100) / 100,
          changePercent: Math.round((change / stock.price) * 10000) / 100,
          history: [...stock.history.slice(-9), newPrice]
        }};
      }}));
      setLastUpdate(new Date());
    }}, 3000);
    return () => clearInterval(interval);
  }}, []);

  return (<div>...</div>);
}}
export default App;

OUTPUT FORMAT (strict JSON):
{{
    "title": "Dashboard Title",
    "components": {{
        "App": "// Complete dashboard with simulated live data as shown above"
    }}
}}

Generate now:"""


# Single-shot form generator
FORM_PROMPT = """You are an expert React developer. Create a functional form with validation.

USER REQUEST:
{user_prompt}

""" + BASE_RULES + """

FORM-SPECIFIC RULES:
1. Form must WORK with proper state management for each field
2. Include validation with error messages shown inline
3. Show success message on valid submit
4. Make it accessible and user-friendly
5. Use useState for form state and errors

OUTPUT FORMAT (strict JSON):
{{
    "title": "Form Title",
    "components": {{
        "App": "import React, {{ useState }} from 'react';\\n\\nfunction App() {{\\n  const [form, setForm] = useState({{}}); // form code\\n}}\\n\\nexport default App;"
    }}
}}

Generate now:"""


# Modification prompt for quick updates
MODIFY_PROMPT = """You are an expert React developer. You are making a MODIFICATION to an existing website.

CURRENT CODE (the existing website to modify):
{current_code}

CLIENT CONTEXT AND MODIFICATION REQUEST:
{user_request}

CRITICAL UNDERSTANDING:
- The "ORIGINAL CLIENT REQUEST" tells you what the website is FOR (e.g., stocks trader, hairdresser, etc.)
- The "CURRENT MODIFICATION REQUEST" tells you what CHANGE to make
- You must KEEP the website's purpose and content, only applying the requested change
- Example: If original was "stocks trader website" and modification is "make background red",
  you keep ALL the stocks trading content and just change the background color to red

ABSOLUTE RULES:
1. Return ONLY the code - no markdown, no backticks, no explanation
2. Use ONLY inline styles  
3. KEEP all existing functionality and content unless explicitly asked to remove it
4. Only change what the CURRENT MODIFICATION REQUEST asks for
5. Maintain the website's original purpose and theme
6. Use Apple San Francisco fonts: fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif"

Return ONLY the complete modified component code, starting with import and ending with export:"""


def get_prompt_for_type(app_type: str) -> str:
    """Get the appropriate prompt template for the app type"""
    prompts = {
        'website': WEBSITE_PROMPT,
        'tool': TOOL_PROMPT,
        'dashboard': DASHBOARD_PROMPT,
        'form': FORM_PROMPT,
        'game': TOOL_PROMPT,  # Games use same structure as tools
    }
    return prompts.get(app_type, WEBSITE_PROMPT)
