const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1920, height: 1080 });
    
    // Use the existing session
    const sessionToken = 'aUA2GRLQP0kmqkxunKm7-A05Js4eNzfraqt3YCcVObY';
    
    // Wait for modification to complete
    console.log('Waiting for modification to complete...');
    let newUrl = null;
    for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 3000));
        const statusResp = await fetch('https://faibric-api.onrender.com/api/onboarding/status/' + sessionToken + '/');
        const status = await statusResp.json();
        console.log('Poll ' + (i+1) + ': status=' + status.status + ', url=' + (status.deployment_url || '').substring(0, 50));
        
        if (status.status === 'deployed' && status.deployment_url) {
            newUrl = status.deployment_url;
            console.log('Modification deployed:', newUrl);
            break;
        }
    }
    
    if (!newUrl) {
        console.log('FAILED: Modification did not complete');
        await browser.close();
        process.exit(1);
    }
    
    // Go to Builder
    const builderUrl = newUrl + '/faibric';
    console.log('Opening Builder:', builderUrl);
    await page.goto(builderUrl, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(2000);
    
    // Login
    await page.fill('input[type="password"]', 'faibric123');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(2000);
    
    // Go to Builder tab
    await page.click('button:has-text("Builder")');
    await page.waitForTimeout(3000);
    
    // Wait for iframe to load
    await page.waitForTimeout(5000);
    
    // Take screenshot
    const screenshotPath = '/Users/abram/Code/Faibric/docs/CUSTOMER_TEST_BUILDER_FINAL.png';
    await page.screenshot({ path: screenshotPath, fullPage: false });
    console.log('Screenshot saved:', screenshotPath);
    
    await browser.close();
})();
