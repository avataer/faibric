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
DASHBOARD_PROMPT = """You are an expert React developer. Create a data dashboard with REAL live data.

USER REQUEST:
{user_prompt}

""" + BASE_RULES.replace("3. NEVER use fetch(), axios, or any HTTP requests - browsers block CORS", "3. For stock data ONLY: use fetch('http://localhost:8000/api/stocks/?symbols=AAPL,GOOGL,MSFT,TSLA,AMZN')") + """

DASHBOARD-SPECIFIC RULES:
1. For STOCK dashboards: Fetch REAL data from Faibric API:
   - URL: http://localhost:8000/api/stocks/?symbols=AAPL,GOOGL,MSFT,TSLA,AMZN
   - Response format: {{ stocks: [{{ symbol, price, change, changePercent, marketState }}] }}
   - Refresh every 30 seconds (API has rate limits)
2. Show loading state while fetching
3. Show green for positive change, red for negative
4. Display marketState (REGULAR, PRE, POST, CLOSED)
5. Create charts using colored DIVs (bar charts)
6. Dark theme: background #0f0f0f or #1a1a2e

EXAMPLE PATTERN FOR REAL STOCK DATA (MUST include imports!):
import React, {{ useState, useEffect }} from 'react';

function App() {{
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {{
    const fetchStocks = async () => {{
      try {{
        const res = await fetch('http://localhost:8000/api/stocks/?symbols=AAPL,GOOGL,MSFT,TSLA,AMZN');
        const data = await res.json();
        setStocks(data.stocks);
        setLoading(false);
      }} catch (err) {{ console.error(err); }}
    }};
    fetchStocks();
    const interval = setInterval(fetchStocks, 30000);
    return () => clearInterval(interval);
  }}, []);

  return (<div>...</div>);
}}
export default App;

OUTPUT FORMAT (strict JSON):
{{
    "title": "Dashboard Title",
    "components": {{
        "App": "// Complete dashboard using the real stock API pattern above"
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
MODIFY_PROMPT = """You are an expert React developer. Modify or completely rewrite this component based on the user's request.

CURRENT CODE:
{current_code}

USER REQUEST:
{user_request}

ABSOLUTE RULES:
1. Return ONLY the code - no markdown, no backticks, no explanation
2. Use ONLY inline styles
3. For STOCK/FINANCIAL data: Use the Faibric API:
   fetch('http://localhost:8000/api/stocks/?symbols=AAPL,GOOGL,MSFT,TSLA,AMZN')
   Response: {{ stocks: [{{ symbol, price, change, changePercent, marketState }}] }}
4. For OTHER data: hardcode realistic values in useState
5. If user wants something completely different, generate a NEW component from scratch
6. Always include loading states for API calls

STOCK API PATTERN:
const [stocks, setStocks] = useState([]);
useEffect(() => {{
  fetch('http://localhost:8000/api/stocks/?symbols=AAPL,GOOGL')
    .then(r => r.json())
    .then(d => setStocks(d.stocks));
}}, []);

Return ONLY the complete component code, starting with import and ending with export:"""


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
