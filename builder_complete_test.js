const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Create site
    console.log('Creating site...');
    const createResp = await fetch('https://faibric-api.onrender.com/api/onboarding/start-dev/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request: 'Build a coffee shop website' })
    });
    const { session_token } = await createResp.json();
    console.log('Session:', session_token);
    
    // Wait for deployment
    console.log('Waiting for initial deployment...');
    let deployedUrl = null;
    for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 5000));
        const status = await (await fetch('https://faibric-api.onrender.com/api/onboarding/status/' + session_token + '/')).json();
        if (status.deployment_url) {
            deployedUrl = status.deployment_url;
            console.log('Deployed:', deployedUrl);
            break;
        }
    }
    
    // Go to Builder
    console.log('Opening Builder...');
    await page.goto(deployedUrl + '/faibric', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2000);
    
    // Login
    await page.fill('input[type="password"]', 'faibric123');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(2000);
    
    // Go to Builder tab
    await page.click('button:has-text("Builder")');
    await page.waitForTimeout(3000);
    
    // Send modification and STAY on this page
    console.log('Sending modification...');
    await page.fill('input[placeholder*="Describe"]', 'make header background green');
    await page.click('button:has-text("Send")');
    
    // Wait for completion message to appear in chat
    console.log('Waiting for modification to complete...');
    let foundComplete = false;
    for (let i = 0; i < 60; i++) {
        await page.waitForTimeout(2000);
        const content = await page.content();
        
        // Check for completion indicators
        if (content.includes('Changes deployed') || content.includes('Refreshing preview')) {
            console.log('Found completion message at ' + (i+1)*2 + 's');
            foundComplete = true;
            await page.waitForTimeout(10000); // Wait for preview to refresh
            break;
        }
        
        // Also check for progress messages
        if (content.includes('AI modifying')) {
            console.log('AI is modifying code...');
        }
        if (content.includes('Deploying')) {
            console.log('Deploying changes...');
        }
    }
    
    // Take final screenshot showing chat + preview
    const screenshotPath = '/Users/abram/Code/Faibric/docs/CUSTOMER_TEST_BUILDER_COMPLETE.png';
    await page.screenshot({ path: screenshotPath });
    console.log('Screenshot saved:', screenshotPath);
    console.log('Completion found:', foundComplete);
    
    await browser.close();
})();
