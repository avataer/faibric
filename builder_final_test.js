const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Create new site
    console.log('Creating site...');
    const createResp = await fetch('https://faibric-api.onrender.com/api/onboarding/start-dev/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request: 'Build a bakery website' })
    });
    const createData = await createResp.json();
    const session_token = createData.session_token;
    console.log('Session:', session_token);

    // Wait for initial deployment
    console.log('Waiting for initial deployment...');
    let deployedUrl = null;
    for (let i = 0; i < 90; i++) {
        await new Promise(r => setTimeout(r, 3000));
        const status = await (await fetch('https://faibric-api.onrender.com/api/onboarding/status/' + session_token + '/')).json();
        console.log('Poll', i+1, '- status:', status.status);
        if (status.deployment_url && status.status === 'deployed') {
            deployedUrl = status.deployment_url;
            console.log('Deployed:', deployedUrl);
            break;
        }
    }

    if (!deployedUrl) {
        console.log('ERROR: Site not deployed');
        await browser.close();
        return;
    }

    // Open Builder
    console.log('Opening Builder...');
    await page.goto(deployedUrl + '/faibric', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(3000);

    // Login
    console.log('Logging in...');
    await page.fill('input[type="password"]', 'faibric123');
    await page.click('button:has-text("Login")');
    await page.waitForTimeout(3000);

    // Go to Builder tab
    console.log('Going to Builder tab...');
    await page.click('button:has-text("Builder")');
    await page.waitForTimeout(5000);

    // Send modification
    console.log('Sending modification: make header bright red...');
    await page.fill('input[placeholder*="Describe"]', 'make the header background bright red');
    await page.click('button:has-text("Send")');

    // Wait for modification to complete by polling API
    console.log('Waiting for modification...');
    let newUrl = null;
    for (let i = 0; i < 90; i++) {
        await page.waitForTimeout(2000);
        const status = await (await fetch('https://faibric-api.onrender.com/api/onboarding/status/' + session_token + '/')).json();
        console.log('Poll', i+1, '- status:', status.status, '- url changed:', status.deployment_url !== deployedUrl);

        if (status.deployment_url && status.deployment_url !== deployedUrl && status.status === 'deployed') {
            newUrl = status.deployment_url;
            console.log('NEW URL:', newUrl);
            break;
        }
    }

    // Wait for preview to refresh
    console.log('Waiting for preview refresh...');
    await page.waitForTimeout(15000);

    // Take screenshot
    const screenshotPath = '/Users/abram/Code/Faibric/docs/CUSTOMER_TEST_BUILDER_FINAL.png';
    await page.screenshot({ path: screenshotPath });
    console.log('Screenshot:', screenshotPath);

    // Verify red in new deployment
    if (newUrl) {
        const html = await (await fetch(newUrl)).text();
        const redCount = (html.match(/red-|bg-red|#[fF][0-9a-fA-F]{2}0000|rgb\(255/gi) || []).length;
        console.log('Red classes/colors found:', redCount);
    }

    console.log('\n=== SUMMARY ===');
    console.log('Initial URL:', deployedUrl);
    console.log('New URL:', newUrl || 'NOT DETECTED');
    console.log('URL Changed:', newUrl && newUrl !== deployedUrl ? 'PASS' : 'FAIL');

    await browser.close();
})();
