const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });
    
    // Step 1: Create a site first via API
    console.log('Creating site via API...');
    const createResp = await fetch('https://faibric-api.onrender.com/api/onboarding/start-dev/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request: 'Build a simple portfolio for a photographer' })
    });
    const createData = await createResp.json();
    console.log('Session:', createData.session_token);
    
    // Step 2: Wait for deployment
    console.log('Waiting for deployment...');
    let deployedUrl = null;
    for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 5000));
        const statusResp = await fetch('https://faibric-api.onrender.com/api/onboarding/status/' + createData.session_token + '/');
        const status = await statusResp.json();
        if (status.deployment_url) {
            deployedUrl = status.deployment_url;
            console.log('Deployed:', deployedUrl);
            break;
        }
        console.log('Poll ' + (i+1) + ': ' + status.build_progress + '%');
    }
    
    if (!deployedUrl) {
        console.log('FAILED: No deployment');
        await browser.close();
        process.exit(1);
    }
    
    // Step 3: Go to the Builder (admin cabinet)
    const builderUrl = deployedUrl + '/faibric';
    console.log('Opening Builder:', builderUrl);
    await page.goto(builderUrl, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of login page
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/debug_login.png' });
    
    // Enter password and click Login
    console.log('Logging in...');
    try {
        await page.fill('input[type="password"]', 'faibric123');
        await page.click('button:has-text("Login")');
        await page.waitForTimeout(3000);
    } catch (e) {
        console.log('Login error:', e.message);
    }
    
    // Take screenshot after login
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/debug_after_login.png' });
    
    // Click on Builder tab
    console.log('Clicking Builder tab...');
    try {
        await page.click('button:has-text("Builder")', { timeout: 10000 });
        await page.waitForTimeout(2000);
    } catch (e) {
        console.log('Builder tab error:', e.message);
    }
    
    // Take screenshot of Builder
    await page.screenshot({ path: '/Users/abram/Code/Faibric/docs/debug_builder.png' });
    
    // Step 4: Send modification via the chat
    console.log('Sending modification...');
    try {
        await page.fill('input[placeholder*="Describe"]', 'make all headings blue color');
        await page.click('button:has-text("Send")');
        console.log('Modification sent, waiting 90s for completion...');
        
        // Wait for "Changes deployed" message
        for (let i = 0; i < 30; i++) {
            await page.waitForTimeout(3000);
            const content = await page.content();
            if (content.includes('Changes deployed') || content.includes('Refreshing preview')) {
                console.log('Modification complete!');
                await page.waitForTimeout(5000); // Extra wait for preview to load
                break;
            }
            console.log('Waiting... ' + (i+1)*3 + 's');
        }
    } catch (e) {
        console.log('Modification error:', e.message);
    }
    
    // Take final screenshot
    const screenshotPath = '/Users/abram/Code/Faibric/docs/customer_test_builder_ui.png';
    console.log('Taking final screenshot...');
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log('Screenshot saved:', screenshotPath);
    
    await browser.close();
    console.log('Done!');
})();
