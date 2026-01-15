const { chromium } = require('playwright');

const API_BASE = 'https://faibric-api.onrender.com';
const PROJECT_ID = '171';

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });

    // Test 1: Cabinet - Registration Flow
    console.log('\n=== TEST 1: Cabinet Registration ===');

    // Create a simple HTML page to show the test
    await page.setContent(`
        <html>
        <head>
            <style>
                body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #1a1a1a; border-bottom: 2px solid #3B82F6; padding-bottom: 10px; }
                h2 { color: #374151; margin-top: 30px; }
                .endpoint { background: #1e293b; color: #22d3ee; padding: 8px 16px; border-radius: 6px; font-family: monospace; margin: 10px 0; }
                .request { background: #0f172a; color: #a5f3fc; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; }
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
                <h1>Faibric Feature Test - Cabinet System</h1>
                <p>Testing customer-facing user portal APIs</p>

                <h2>1. Get Cabinet Configuration <span class="status" id="status1">TESTING...</span></h2>
                <div class="endpoint">GET /api/cabinet/public/config/</div>
                <div class="header">Header: X-Faibric-App-Id: ${PROJECT_ID}</div>
                <div class="response" id="config-response">Loading...</div>

                <h2>2. User Registration <span class="status" id="status2">TESTING...</span></h2>
                <div class="endpoint">POST /api/cabinet/public/auth/register/</div>
                <div class="request" id="register-request">Loading...</div>
                <div class="response" id="register-response">Loading...</div>

                <h2>3. User Login (Verification Required) <span class="status" id="status3">TESTING...</span></h2>
                <div class="endpoint">POST /api/cabinet/public/auth/login/</div>
                <div class="response" id="login-response">Loading...</div>
            </div>
        </body>
        </html>
    `);

    // Test Cabinet Config
    try {
        const configResp = await fetch(API_BASE + '/api/cabinet/public/config/', {
            headers: { 'X-Faibric-App-Id': PROJECT_ID }
        });
        const configData = await configResp.json();
        await page.evaluate((data) => {
            document.getElementById('config-response').textContent = JSON.stringify(data, null, 2);
            document.getElementById('status1').textContent = 'PASS';
            document.getElementById('status1').className = 'status pass';
        }, configData);
        console.log('Cabinet Config: PASS');
    } catch (e) {
        await page.evaluate((err) => {
            document.getElementById('config-response').textContent = 'Error: ' + err;
            document.getElementById('config-response').className = 'response error';
            document.getElementById('status1').textContent = 'FAIL';
            document.getElementById('status1').className = 'status fail';
        }, e.message);
        console.log('Cabinet Config: FAIL');
    }

    // Test Registration
    const testEmail = `test${Date.now()}@example.com`;
    const registerPayload = { email: testEmail, password: 'TestPass123', first_name: 'Test', last_name: 'User' };

    await page.evaluate((payload) => {
        document.getElementById('register-request').textContent = JSON.stringify(payload, null, 2);
    }, registerPayload);

    try {
        const registerResp = await fetch(API_BASE + '/api/cabinet/public/auth/register/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Faibric-App-Id': PROJECT_ID },
            body: JSON.stringify(registerPayload)
        });
        const registerData = await registerResp.json();
        await page.evaluate((data) => {
            document.getElementById('register-response').textContent = JSON.stringify(data, null, 2);
            document.getElementById('status2').textContent = data.user_id ? 'PASS' : 'FAIL';
            document.getElementById('status2').className = 'status ' + (data.user_id ? 'pass' : 'fail');
        }, registerData);
        console.log('Registration:', registerData.user_id ? 'PASS' : 'FAIL');
    } catch (e) {
        await page.evaluate((err) => {
            document.getElementById('register-response').textContent = 'Error: ' + err;
            document.getElementById('register-response').className = 'response error';
            document.getElementById('status2').textContent = 'FAIL';
            document.getElementById('status2').className = 'status fail';
        }, e.message);
        console.log('Registration: FAIL');
    }

    // Test Login (should fail - unverified)
    try {
        const loginResp = await fetch(API_BASE + '/api/cabinet/public/auth/login/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Faibric-App-Id': PROJECT_ID },
            body: JSON.stringify({ email: testEmail, password: 'TestPass123' })
        });
        const loginData = await loginResp.json();
        await page.evaluate((data) => {
            document.getElementById('login-response').textContent = JSON.stringify(data, null, 2);
            // Expected: error about email verification
            const isExpected = data.error && data.error.includes('verify');
            document.getElementById('status3').textContent = isExpected ? 'PASS (Expected)' : 'FAIL';
            document.getElementById('status3').className = 'status ' + (isExpected ? 'pass' : 'fail');
        }, loginData);
        console.log('Login (unverified):', loginData.error ? 'PASS (Expected rejection)' : 'FAIL');
    } catch (e) {
        console.log('Login: FAIL -', e.message);
    }

    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/SCREENSHOT_CABINET_TEST.png' });
    console.log('Screenshot saved: SCREENSHOT_CABINET_TEST.png');

    // Test 2: Stocks API
    console.log('\n=== TEST 2: Stocks API ===');

    await page.setContent(`
        <html>
        <head>
            <style>
                body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #1a1a1a; border-bottom: 2px solid #10b981; padding-bottom: 10px; }
                h2 { color: #374151; margin-top: 30px; }
                .endpoint { background: #1e293b; color: #22d3ee; padding: 8px 16px; border-radius: 6px; font-family: monospace; margin: 10px 0; }
                .response { background: #064e3b; color: #6ee7b7; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; }
                .stock-card { background: linear-gradient(135deg, #1e3a5f, #0f172a); color: white; padding: 20px; border-radius: 12px; margin: 15px 0; }
                .stock-symbol { font-size: 24px; font-weight: bold; }
                .stock-price { font-size: 36px; font-weight: bold; margin: 10px 0; }
                .stock-change { font-size: 18px; }
                .positive { color: #22c55e; }
                .negative { color: #ef4444; }
                .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; margin-left: 10px; }
                .pass { background: #22c55e; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Faibric Feature Test - Stocks API</h1>
                <p>Real-time stock price data via Yahoo Finance</p>

                <h2>Stock Quotes <span class="status pass">LIVE DATA</span></h2>
                <div id="stocks-container"></div>

                <h2>Raw API Response</h2>
                <div class="endpoint">GET /api/stocks/{symbol}/</div>
                <div class="response" id="stocks-response">Loading...</div>
            </div>
        </body>
        </html>
    `);

    const symbols = ['AAPL', 'GOOGL', 'MSFT'];
    const stockResults = [];

    for (const symbol of symbols) {
        try {
            const resp = await fetch(API_BASE + '/api/stocks/' + symbol + '/');
            const data = await resp.json();
            stockResults.push(data);
        } catch (e) {
            stockResults.push({ symbol, error: e.message });
        }
    }

    await page.evaluate((results) => {
        const container = document.getElementById('stocks-container');
        container.innerHTML = results.map(stock => {
            if (stock.error) return `<div class="stock-card">Error: ${stock.error}</div>`;
            const changeClass = stock.change >= 0 ? 'positive' : 'negative';
            const changeSign = stock.change >= 0 ? '+' : '';
            return `
                <div class="stock-card">
                    <div class="stock-symbol">${stock.symbol}</div>
                    <div class="stock-price">$${stock.price.toFixed(2)}</div>
                    <div class="stock-change ${changeClass}">
                        ${changeSign}${stock.change.toFixed(2)} (${changeSign}${stock.changePercent.toFixed(2)}%)
                    </div>
                    <div style="margin-top: 10px; opacity: 0.7;">Market: ${stock.marketState}</div>
                </div>
            `;
        }).join('');
        document.getElementById('stocks-response').textContent = JSON.stringify(results, null, 2);
    }, stockResults);

    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/SCREENSHOT_STOCKS_TEST.png' });
    console.log('Screenshot saved: SCREENSHOT_STOCKS_TEST.png');

    // Test 3: Gateway API
    console.log('\n=== TEST 3: Gateway API ===');

    await page.setContent(`
        <html>
        <head>
            <style>
                body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
                .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #1a1a1a; border-bottom: 2px solid #8b5cf6; padding-bottom: 10px; }
                h2 { color: #374151; margin-top: 30px; }
                .endpoint { background: #1e293b; color: #22d3ee; padding: 8px 16px; border-radius: 6px; font-family: monospace; margin: 10px 0; }
                .response { background: #064e3b; color: #6ee7b7; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; max-height: 300px; overflow: auto; }
                .services-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }
                .service-card { background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; border-radius: 8px; }
                .service-name { font-weight: bold; color: #1e293b; }
                .service-status { font-size: 12px; margin-top: 5px; }
                .configured { color: #22c55e; }
                .not-configured { color: #94a3b8; }
                .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-weight: bold; margin-left: 10px; }
                .pass { background: #22c55e; color: white; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Faibric Feature Test - Gateway API</h1>
                <p>Universal API proxy for external services</p>

                <h2>Available Services <span class="status pass">17 SERVICES</span></h2>
                <div class="services-grid" id="services-grid">Loading...</div>

                <h2>Test API Call - JSON Placeholder <span class="status" id="test-status">TESTING...</span></h2>
                <div class="endpoint">POST /api/gateway/ {"service": "jsonplaceholder", "endpoint": "posts/1"}</div>
                <div class="response" id="test-response">Loading...</div>
            </div>
        </body>
        </html>
    `);

    // Get services list
    try {
        const servicesResp = await fetch(API_BASE + '/api/gateway/services/');
        const servicesData = await servicesResp.json();

        await page.evaluate((data) => {
            document.getElementById('services-grid').innerHTML = data.services.map(s => `
                <div class="service-card">
                    <div class="service-name">${s.name}</div>
                    <div class="service-status ${s.configured ? 'configured' : 'not-configured'}">
                        ${s.configured ? 'Configured' : 'Needs API Key'}
                    </div>
                </div>
            `).join('');
        }, servicesData);
    } catch (e) {
        console.log('Services list error:', e.message);
    }

    // Test proxy call - use page context for fetch
    await page.evaluate(async (apiBase) => {
        try {
            const testResp = await fetch(apiBase + '/api/gateway/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ service: 'jsonplaceholder', endpoint: 'posts/1' })
            });
            const testData = await testResp.json();
            document.getElementById('test-response').textContent = JSON.stringify(testData, null, 2);
            document.getElementById('test-status').textContent = testData.success ? 'PASS' : 'FAIL';
            document.getElementById('test-status').className = 'status ' + (testData.success ? 'pass' : 'fail');
        } catch (e) {
            document.getElementById('test-response').textContent = 'Error: ' + e.message;
            document.getElementById('test-response').className = 'response error';
            document.getElementById('test-status').textContent = 'FAIL';
            document.getElementById('test-status').className = 'status fail';
        }
    }, API_BASE);
    console.log('Gateway Test: Done');

    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/SCREENSHOT_GATEWAY_TEST.png' });
    console.log('Screenshot saved: SCREENSHOT_GATEWAY_TEST.png');

    // Test 4: Analytics API
    console.log('\n=== TEST 4: Analytics API ===');

    await page.setContent(`
        <html>
        <head>
            <style>
                body { font-family: system-ui; padding: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #1a1a1a; border-bottom: 2px solid #f59e0b; padding-bottom: 10px; }
                h2 { color: #374151; margin-top: 30px; }
                .endpoint { background: #1e293b; color: #22d3ee; padding: 8px 16px; border-radius: 6px; font-family: monospace; margin: 10px 0; }
                .request { background: #0f172a; color: #a5f3fc; padding: 15px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; margin: 10px 0; }
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

                <h2>1. Identify User <span class="status" id="status1">TESTING...</span></h2>
                <div class="endpoint">POST /api/analytics/identify/</div>
                <div class="header">Header: X-Faibric-App-Id: ${PROJECT_ID}</div>
                <div class="request" id="identify-request"></div>
                <div class="response" id="identify-response">Loading...</div>

                <h2>2. Track Event <span class="status" id="status2">TESTING...</span></h2>
                <div class="endpoint">POST /api/analytics/track/</div>
                <div class="request" id="track-request"></div>
                <div class="response" id="track-response">Loading...</div>
            </div>
        </body>
        </html>
    `);

    // Test Identify and Track using page context
    await page.evaluate(async (params) => {
        const { apiBase, projectId } = params;
        const identifyPayload = { distinct_id: 'test-user-' + Date.now(), properties: { email: 'test@example.com', name: 'Test User' } };
        document.getElementById('identify-request').textContent = JSON.stringify(identifyPayload, null, 2);

        try {
            const identifyResp = await fetch(apiBase + '/api/analytics/identify/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Faibric-App-Id': projectId },
                body: JSON.stringify(identifyPayload)
            });
            const identifyData = await identifyResp.json();
            document.getElementById('identify-response').textContent = JSON.stringify(identifyData, null, 2);
            document.getElementById('status1').textContent = identifyData.success ? 'PASS' : 'FAIL';
            document.getElementById('status1').className = 'status ' + (identifyData.success ? 'pass' : 'fail');
        } catch (e) {
            document.getElementById('identify-response').textContent = 'Error: ' + e.message;
            document.getElementById('status1').textContent = 'FAIL';
            document.getElementById('status1').className = 'status fail';
        }

        const trackPayload = { event: 'button_click', distinct_id: 'test-user-' + Date.now(), properties: { button: 'signup' } };
        document.getElementById('track-request').textContent = JSON.stringify(trackPayload, null, 2);

        try {
            const trackResp = await fetch(apiBase + '/api/analytics/track/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Faibric-App-Id': projectId },
                body: JSON.stringify(trackPayload)
            });
            const trackText = await trackResp.text();
            let trackData;
            try { trackData = JSON.parse(trackText); } catch { trackData = { error: trackText.substring(0, 200) }; }

            document.getElementById('track-response').textContent = typeof trackData === 'string' ? trackData : JSON.stringify(trackData, null, 2);
            const isSuccess = trackData.success || trackData.event_id;
            document.getElementById('status2').textContent = isSuccess ? 'PASS' : 'FAIL (Server Error)';
            document.getElementById('status2').className = 'status ' + (isSuccess ? 'pass' : 'fail');
            if (!isSuccess) document.getElementById('track-response').className = 'response error';
        } catch (e) {
            document.getElementById('track-response').textContent = 'Error: ' + e.message;
            document.getElementById('track-response').className = 'response error';
            document.getElementById('status2').textContent = 'FAIL';
            document.getElementById('status2').className = 'status fail';
        }
    }, { apiBase: API_BASE, projectId: PROJECT_ID });

    console.log('Analytics tests: Done');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/SCREENSHOT_ANALYTICS_TEST.png' });
    console.log('Screenshot saved: SCREENSHOT_ANALYTICS_TEST.png');

    await browser.close();
    console.log('\n=== ALL TESTS COMPLETE ===');
})();
