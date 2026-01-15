const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Create new site
    console.log('Creating site...');
    const resp = await fetch('https://faibric-api.onrender.com/api/onboarding/start-dev/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request: 'Build a yoga studio website with class schedule' })
    });
    const { session_token } = await resp.json();
    console.log('Session:', session_token);
    
    // Wait for deployment
    console.log('Waiting for deployment...');
    let url = null;
    for (let i = 0; i < 60 && !url; i++) {
        await new Promise(r => setTimeout(r, 5000));
        const status = await (await fetch('https://faibric-api.onrender.com/api/onboarding/status/' + session_token + '/')).json();
        if (status.deployment_url && status.deployment_url.includes('vercel')) {
            url = status.deployment_url;
            console.log('Vercel deployment:', url);
        }
        console.log('Poll', i+1);
    }
    
    if (!url) { console.log('No Vercel deployment'); process.exit(1); }
    
    // Open Builder
    console.log('Opening Builder...');
    await page.goto(url + '/faibric', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2000);
    await page.fill('input[type="password"]', 'faibric123');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(2000);
    await page.click('button:has-text("Builder")');
    await page.waitForTimeout(3000);
    
    // Send modification
    console.log('Sending: make header purple...');
    await page.fill('input[placeholder*="Describe"]', 'make the header background purple');
    await page.click('button:has-text("Send")');
    
    // Wait for FULL completion - poll API for URL change
    console.log('Waiting for URL to change (indicates modification deployed)...');
    let newUrl = null;
    for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 3000));
        const status = await (await fetch('https://faibric-api.onrender.com/api/onboarding/status/' + session_token + '/')).json();
        
        if (status.deployment_url && status.deployment_url !== url && status.deployment_url.includes('vercel')) {
            newUrl = status.deployment_url;
            console.log('URL CHANGED to:', newUrl);
            break;
        }
        console.log('Poll', i+1, '- status:', status.status);
    }
    
    if (newUrl) {
        // Verify purple in new deployment
        const html = await (await fetch(newUrl)).text();
        console.log('Purple classes in new deployment:', (html.match(/purple/gi) || []).length);
        
        // Wait a bit more for iframe in browser to update
        await page.waitForTimeout(8000);
    }
    
    // Take screenshot - should show chat on left, modified preview on right
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/CUSTOMER_TEST_BUILDER_PURPLE.png' });
    console.log('Screenshot saved');
    
    // Output report data
    console.log('\n=== CUSTOMER TEST REPORT ===');
    console.log('Session:', session_token);
    console.log('Initial URL:', url);
    console.log('Modified URL:', newUrl || 'Not changed');
    console.log('Modification: make header purple');
    
    await browser.close();
})();
