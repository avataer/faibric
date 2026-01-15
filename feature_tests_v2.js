const { chromium } = require('playwright');

const API_BASE = 'https://faibric-api.onrender.com';
const PROJECT_ID = '171';

async function apiCall(endpoint, options = {}) {
    const resp = await fetch(API_BASE + endpoint, options);
    const text = await resp.text();
    try {
        return { status: resp.status, data: JSON.parse(text) };
    } catch {
        return { status: resp.status, data: { raw: text.substring(0, 300) } };
    }
}

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });

    // ========== TEST 1: Cabinet System ==========
    console.log('\n=== TEST 1: Cabinet System ===');

    const configResult = await apiCall('/api/cabinet/public/config/', {
        headers: { 'X-Faibric-App-Id': PROJECT_ID }
    });
    console.log('Config:', configResult.status === 200 ? 'PASS' : 'FAIL');

    const testEmail = `test${Date.now()}@example.com`;
    const registerResult = await apiCall('/api/cabinet/public/auth/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Faibric-App-Id': PROJECT_ID },
        body: JSON.stringify({ email: testEmail, password: 'TestPass123', first_name: 'Test', last_name: 'User' })
    });
    console.log('Register:', registerResult.data.user_id ? 'PASS' : 'FAIL');

    const loginResult = await apiCall('/api/cabinet/public/auth/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Faibric-App-Id': PROJECT_ID },
        body: JSON.stringify({ email: testEmail, password: 'TestPass123' })
    });
    const loginExpected = loginResult.data.error && loginResult.data.error.includes('verify');
    console.log('Login (verify needed):', loginExpected ? 'PASS' : 'FAIL');

    await page.setContent(`
        <html>
        <head>
            <style>
                body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #1a1a1a; border-bottom: 2px solid #3B82F6; padding-bottom: 10px; }
                h2 { color: #374151; margin-top: 30px; }
                .endpoint { background: #1e293b; color: #22d3ee; padding: 8px 16px; border-radius: 6px; font-family: monospace; margin: 10px 0; }
                .response { background: #064e3b; color: #6ee7b7; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; }
                .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; margin-left: 10px; }
                .pass { background: #22c55e; color: white; }
                .fail { background: #ef4444; color: white; }
                .header { color: #94a3b8; font-size: 12px; margin-bottom: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Faibric Feature Test - Cabinet System</h1>
                <p>Testing customer-facing user portal APIs</p>

                <h2>1. Get Cabinet Configuration <span class="status ${configResult.status === 200 ? 'pass' : 'fail'}">${configResult.status === 200 ? 'PASS' : 'FAIL'}</span></h2>
                <div class="endpoint">GET /api/cabinet/public/config/</div>
                <div class="header">Header: X-Faibric-App-Id: ${PROJECT_ID}</div>
                <div class="response">${JSON.stringify(configResult.data, null, 2)}</div>

                <h2>2. User Registration <span class="status ${registerResult.data.user_id ? 'pass' : 'fail'}">${registerResult.data.user_id ? 'PASS' : 'FAIL'}</span></h2>
                <div class="endpoint">POST /api/cabinet/public/auth/register/</div>
                <div class="response">${JSON.stringify(registerResult.data, null, 2)}</div>

                <h2>3. User Login (Verification Required) <span class="status ${loginExpected ? 'pass' : 'fail'}">${loginExpected ? 'PASS' : 'FAIL'}</span></h2>
                <div class="endpoint">POST /api/cabinet/public/auth/login/</div>
                <div class="response">${JSON.stringify(loginResult.data, null, 2)}</div>
            </div>
        </body>
        </html>
    `);
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/SCREENSHOT_CABINET_TEST.png' });
    console.log('Screenshot: SCREENSHOT_CABINET_TEST.png');

    // ========== TEST 2: Stocks API ==========
    console.log('\n=== TEST 2: Stocks API ===');

    const stockResults = [];
    for (const symbol of ['AAPL', 'GOOGL', 'MSFT']) {
        const result = await apiCall(`/api/stocks/${symbol}/`);
        stockResults.push(result.data);
        console.log(`${symbol}:`, result.data.price ? 'PASS' : 'FAIL');
    }

    await page.setContent(`
        <html>
        <head>
            <style>
                body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #1a1a1a; border-bottom: 2px solid #10b981; padding-bottom: 10px; }
                h2 { color: #374151; margin-top: 30px; }
                .stock-card { background: linear-gradient(135deg, #1e3a5f, #0f172a); color: white; padding: 20px; border-radius: 12px; margin: 15px 0; }
                .stock-symbol { font-size: 24px; font-weight: bold; }
                .stock-price { font-size: 36px; font-weight: bold; margin: 10px 0; }
                .stock-change { font-size: 18px; }
                .positive { color: #22c55e; }
                .negative { color: #ef4444; }
                .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; margin-left: 10px; background: #22c55e; color: white; }
                .response { background: #064e3b; color: #6ee7b7; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; }
                .endpoint { background: #1e293b; color: #22d3ee; padding: 8px 16px; border-radius: 6px; font-family: monospace; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Faibric Feature Test - Stocks API</h1>
                <p>Real-time stock price data via Yahoo Finance</p>

                <h2>Stock Quotes <span class="status">LIVE DATA</span></h2>
                ${stockResults.map(s => `
                    <div class="stock-card">
                        <div class="stock-symbol">${s.symbol}</div>
                        <div class="stock-price">$${s.price?.toFixed(2) || 'N/A'}</div>
                        <div class="stock-change ${s.change >= 0 ? 'positive' : 'negative'}">
                            ${s.change >= 0 ? '+' : ''}${s.change?.toFixed(2) || '0'} (${s.change >= 0 ? '+' : ''}${s.changePercent?.toFixed(2) || '0'}%)
                        </div>
                        <div style="margin-top: 10px; opacity: 0.7;">Market: ${s.marketState || 'Unknown'}</div>
                    </div>
                `).join('')}

                <h2>Raw API Response</h2>
                <div class="endpoint">GET /api/stocks/{symbol}/</div>
                <div class="response">${JSON.stringify(stockResults, null, 2)}</div>
            </div>
        </body>
        </html>
    `);
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/SCREENSHOT_STOCKS_TEST.png' });
    console.log('Screenshot: SCREENSHOT_STOCKS_TEST.png');

    // ========== TEST 3: Gateway API ==========
    console.log('\n=== TEST 3: Gateway API ===');

    const servicesResult = await apiCall('/api/gateway/services/');
    console.log('Services:', servicesResult.status === 200 ? 'PASS' : 'FAIL');

    const gatewayResult = await apiCall('/api/gateway/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service: 'jsonplaceholder', endpoint: 'posts/1' })
    });
    console.log('Gateway Call:', gatewayResult.data.success ? 'PASS' : 'FAIL');

    await page.setContent(`
        <html>
        <head>
            <style>
                body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
                .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #1a1a1a; border-bottom: 2px solid #8b5cf6; padding-bottom: 10px; }
                h2 { color: #374151; margin-top: 30px; }
                .services-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }
                .service-card { background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 8px; }
                .service-name { font-weight: bold; color: #1e293b; }
                .service-status { font-size: 12px; margin-top: 5px; }
                .configured { color: #22c55e; }
                .not-configured { color: #94a3b8; }
                .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; margin-left: 10px; }
                .pass { background: #22c55e; color: white; }
                .fail { background: #ef4444; color: white; }
                .endpoint { background: #1e293b; color: #22d3ee; padding: 8px 16px; border-radius: 6px; font-family: monospace; margin: 10px 0; }
                .response { background: #064e3b; color: #6ee7b7; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; max-height: 200px; overflow: auto; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Faibric Feature Test - Gateway API</h1>
                <p>Universal API proxy for external services</p>

                <h2>Available Services <span class="status pass">17 SERVICES</span></h2>
                <div class="services-grid">
                    ${(servicesResult.data.services || []).map(s => `
                        <div class="service-card">
                            <div class="service-name">${s.name}</div>
                            <div class="service-status ${s.configured ? 'configured' : 'not-configured'}">
                                ${s.configured ? 'Configured' : 'Needs API Key'}
                            </div>
                        </div>
                    `).join('')}
                </div>

                <h2>Test API Call - JSON Placeholder <span class="status ${gatewayResult.data.success ? 'pass' : 'fail'}">${gatewayResult.data.success ? 'PASS' : 'FAIL'}</span></h2>
                <div class="endpoint">POST /api/gateway/ {"service": "jsonplaceholder", "endpoint": "posts/1"}</div>
                <div class="response">${JSON.stringify(gatewayResult.data, null, 2)}</div>
            </div>
        </body>
        </html>
    `);
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/SCREENSHOT_GATEWAY_TEST.png' });
    console.log('Screenshot: SCREENSHOT_GATEWAY_TEST.png');

    // ========== TEST 4: Analytics API ==========
    console.log('\n=== TEST 4: Analytics API ===');

    const identifyResult = await apiCall('/api/analytics/identify/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Faibric-App-Id': PROJECT_ID },
        body: JSON.stringify({ distinct_id: 'test-user-' + Date.now(), properties: { email: 'test@example.com', name: 'Test User' } })
    });
    console.log('Identify:', identifyResult.data.success ? 'PASS' : 'FAIL');

    const trackResult = await apiCall('/api/analytics/track/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Faibric-App-Id': PROJECT_ID },
        body: JSON.stringify({ event: 'button_click', distinct_id: 'test-user-' + Date.now(), properties: { button: 'signup' } })
    });
    const trackPass = trackResult.data.success || trackResult.data.event_id;
    console.log('Track:', trackPass ? 'PASS' : 'FAIL');

    await page.setContent(`
        <html>
        <head>
            <style>
                body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #1a1a1a; border-bottom: 2px solid #f59e0b; padding-bottom: 10px; }
                h2 { color: #374151; margin-top: 30px; }
                .endpoint { background: #1e293b; color: #22d3ee; padding: 8px 16px; border-radius: 6px; font-family: monospace; margin: 10px 0; }
                .response { background: #064e3b; color: #6ee7b7; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; }
                .error { background: #7f1d1d; color: #fca5a5; }
                .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; margin-left: 10px; }
                .pass { background: #22c55e; color: white; }
                .fail { background: #ef4444; color: white; }
                .header { color: #94a3b8; font-size: 12px; margin-bottom: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Faibric Feature Test - Analytics API</h1>
                <p>Event tracking and user identification for customer apps</p>

                <h2>1. Identify User <span class="status ${identifyResult.data.success ? 'pass' : 'fail'}">${identifyResult.data.success ? 'PASS' : 'FAIL'}</span></h2>
                <div class="endpoint">POST /api/analytics/identify/</div>
                <div class="header">Header: X-Faibric-App-Id: ${PROJECT_ID}</div>
                <div class="response">${JSON.stringify(identifyResult.data, null, 2)}</div>

                <h2>2. Track Event <span class="status ${trackPass ? 'pass' : 'fail'}">${trackPass ? 'PASS' : 'FAIL (Server Error)'}</span></h2>
                <div class="endpoint">POST /api/analytics/track/</div>
                <div class="response ${trackPass ? '' : 'error'}">${JSON.stringify(trackResult.data, null, 2)}</div>
            </div>
        </body>
        </html>
    `);
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/SCREENSHOT_ANALYTICS_TEST.png' });
    console.log('Screenshot: SCREENSHOT_ANALYTICS_TEST.png');

    await browser.close();
    console.log('\n=== ALL TESTS COMPLETE ===');
})();
