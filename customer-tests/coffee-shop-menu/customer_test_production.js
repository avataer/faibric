const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ARTIFACTS_DIR = '/Users/avataer/Code/Faibric/test-artifacts';
const PRODUCTION_URL = 'https://faibric-frontend.onrender.com';

function log(msg) {
    const ts = new Date().toISOString();
    console.log(`[${ts}] ${msg}`);
    fs.appendFileSync(path.join(ARTIFACTS_DIR, 'production_test_log.txt'), `[${ts}] ${msg}\n`);
}

async function run() {
    log('=== PRODUCTION CUSTOMER TEST ===');
    log(`Testing: ${PRODUCTION_URL}`);

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        // Step 1: Open production frontend
        await page.goto(PRODUCTION_URL, { waitUntil: 'networkidle', timeout: 60000 });
        log('Loaded production frontend');

        // Click "Start New" if visible
        const startNew = page.locator('button:has-text("Start New")').first();
        if (await startNew.isVisible().catch(() => false)) {
            await startNew.click();
            await page.waitForTimeout(2000);
        }

        // Step 2: Submit initial request
        log('Submitting initial request...');
        const textarea = page.locator('textarea').first();
        await textarea.fill('Create a coffee shop menu for "Bean & Brew" with cream and brown colors');

        await page.locator('button:has-text("Start Building")').first().click();
        log('Build started');

        // Wait for deployment (up to 4 minutes)
        log('Waiting for initial deployment...');
        let deployed = false;
        let deploymentUrl = null;
        const startTime = Date.now();
        const maxWait = 240000; // 4 minutes

        while (!deployed && Date.now() - startTime < maxWait) {
            const deployedBtn = page.locator('button:has-text("Deployed")').first();
            if (await deployedBtn.isVisible().catch(() => false)) {
                deployed = true;
                log('Initial deployment complete!');
            } else {
                await page.waitForTimeout(5000);
                const elapsed = Math.round((Date.now() - startTime) / 1000);
                log(`Building... ${elapsed}s`);
            }
        }

        if (!deployed) {
            throw new Error('Initial deployment timed out after 4 minutes');
        }

        await page.waitForTimeout(3000);

        // Get deployment URL
        const bodyText = await page.textContent('body');
        const urlMatch = bodyText.match(/https:\/\/[^\s]+\.vercel\.app/);
        if (urlMatch) {
            deploymentUrl = urlMatch[0];
            log(`Initial deployment URL: ${deploymentUrl}`);
        }

        // Take screenshot
        await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'production_01_initial.png'), fullPage: true });
        log('Screenshot: Initial deployment');

        // Step 5: Send chat amendment
        log('Sending chat amendment: Add phone number 555-123-4567 at top');
        const chatInput = page.locator('textarea').first();
        await chatInput.fill('Add a phone number 555-123-4567 at the very top in large bold text');
        
        // Try different ways to submit
        const sendIcon = page.locator('button svg').first();
        if (await sendIcon.isVisible().catch(() => false)) {
            await sendIcon.click();
        } else {
            await page.keyboard.press('Enter');
        }
        log('Amendment request sent');

        // Wait for NEW URL (race condition test)
        log('Waiting for amendment to deploy (testing race condition fix)...');
        await page.waitForTimeout(2000);

        let newUrl = null;
        const amendStart = Date.now();
        const amendMaxWait = 180000; // 3 minutes

        while (!newUrl && Date.now() - amendStart < amendMaxWait) {
            await page.waitForTimeout(5000);
            const newBodyText = await page.textContent('body');
            const newUrlMatch = newBodyText.match(/https:\/\/[^\s]+\.vercel\.app/);
            
            if (newUrlMatch && newUrlMatch[0] !== deploymentUrl) {
                newUrl = newUrlMatch[0];
                log(`NEW deployment URL: ${newUrl}`);
                log('SUCCESS: URL changed after amendment!');
            } else {
                const elapsed = Math.round((Date.now() - amendStart) / 1000);
                log(`Waiting for new URL... ${elapsed}s`);
            }
        }

        // Take final screenshot
        await page.waitForTimeout(3000);
        await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'production_02_amendment.png'), fullPage: true });
        log('Screenshot: Amendment result');

        // Verify results
        if (newUrl && newUrl !== deploymentUrl) {
            log('=== TEST PASSED ===');
            log('Race condition fix verified on production!');
            
            // Check deployed site for phone number
            const browser2 = await chromium.launch({ headless: true });
            const page2 = await browser2.newPage();
            await page2.goto(newUrl, { waitUntil: 'networkidle', timeout: 30000 });
            const content = await page2.textContent('body');
            
            if (content.includes('555') || content.includes('phone')) {
                log('Phone number visible in amended site!');
            }
            
            await page2.screenshot({ path: path.join(ARTIFACTS_DIR, 'production_03_amended_site.png'), fullPage: true });
            log('Screenshot: Amended deployed site');
            await browser2.close();
            
            return { success: true, oldUrl: deploymentUrl, newUrl: newUrl };
        } else {
            log('=== TEST FAILED ===');
            log('URL did not change after amendment');
            return { success: false, oldUrl: deploymentUrl, newUrl: null };
        }

    } catch (e) {
        log(`ERROR: ${e.message}`);
        await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'production_error.png') }).catch(() => {});
        throw e;
    } finally {
        await browser.close();
    }
}

run()
    .then(result => {
        console.log(JSON.stringify(result, null, 2));
        process.exit(result.success ? 0 : 1);
    })
    .catch(e => {
        console.error(e);
        process.exit(1);
    });
