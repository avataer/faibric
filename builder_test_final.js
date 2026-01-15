const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    console.log('Creating site via API...');
    const createResp = await fetch('https://faibric-api.onrender.com/api/onboarding/start-dev/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request: 'Build a bakery website with menu section' })
    });
    const createData = await createResp.json();
    const sessionToken = createData.session_token;
    console.log('Session:', sessionToken);
    
    console.log('Waiting for deployment...');
    let deployedUrl = null;
    for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 5000));
        const statusResp = await fetch('https://faibric-api.onrender.com/api/onboarding/status/' + sessionToken + '/');
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
    
    const builderUrl = deployedUrl + '/faibric';
    console.log('Opening Builder:', builderUrl);
    await page.goto(builderUrl, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2000);
    
    console.log('Logging in...');
    await page.fill('input[type="password"]', 'faibric123');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(2000);
    
    console.log('Clicking Builder tab...');
    await page.click('button:has-text("Builder")');
    await page.waitForTimeout(2000);
    
    console.log('Sending modification: make header background red...');
    await page.fill('input[placeholder*="Describe"]', 'make the navigation header background red');
    await page.click('button:has-text("Send")');
    
    console.log('Waiting for modification to complete...');
    for (let i = 0; i < 40; i++) {
        await page.waitForTimeout(3000);
        const content = await page.content();
        if (content.includes('Changes deployed') || content.includes('Refreshing preview')) {
            console.log('Modification complete at ' + (i+1)*3 + 's!');
            await page.waitForTimeout(8000); // Wait for preview iframe to reload
            break;
        }
        console.log('Waiting... ' + (i+1)*3 + 's');
    }
    
    // Take high-res screenshot
    const screenshotPath = '/Users/abram/Code/Faibric/docs/CUSTOMER_TEST_BUILDER_SCREENSHOT.png';
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log('Screenshot saved:', screenshotPath);
    
    // Output info for report
    console.log('\n=== REPORT DATA ===');
    console.log('SESSION_TOKEN=' + sessionToken);
    console.log('INITIAL_URL=' + deployedUrl);
    console.log('BUILDER_URL=' + builderUrl);
    console.log('MODIFICATION=make the navigation header background red');
    
    await browser.close();
})();
