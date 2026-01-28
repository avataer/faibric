const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ARTIFACTS_DIR = '/Users/avataer/Code/Faibric/test-artifacts';

function log(msg) {
    const ts = new Date().toISOString();
    console.log(`[${ts}] ${msg}`);
    fs.appendFileSync(path.join(ARTIFACTS_DIR, 'test_log.txt'), `[${ts}] ${msg}\n`);
}

async function run() {
    log('=== CUSTOMER TEST: Chat Amendment Race Condition ===');
    log('Testing locally at http://localhost:5174');

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        // Step 1: Open local frontend
        await page.goto('http://localhost:5174/', { waitUntil: 'networkidle' });
        log('Loaded local frontend');

        // Click "Start New" if visible
        const startNew = page.locator('button:has-text("Start New")').first();
        if (await startNew.isVisible().catch(() => false)) {
            await startNew.click();
            await page.waitForTimeout(2000);
        }

        // Step 2: Submit initial request
        log('Submitting initial request...');
        const textarea = page.locator('textarea').first();
        await textarea.fill('Create a simple landing page for a pizza restaurant called "Tony\'s Pizza" with a red and white color scheme');

        await page.locator('button:has-text("Start Building")').first().click();
        log('Build started');

        // Wait for deployment (up to 3 minutes)
        log('Waiting for initial deployment...');
        let deployed = false;
        let deploymentUrl = null;
        const startTime = Date.now();
        const maxWait = 180000;

        while (!deployed && Date.now() - startTime < maxWait) {
            const deployedBtn = page.locator('button:has-text("Deployed")').first();
            if (await deployedBtn.isVisible().catch(() => false)) {
                deployed = true;
                log('Initial deployment complete!');
            } else {
                await page.waitForTimeout(3000);
                const elapsed = Math.round((Date.now() - startTime) / 1000);
                log(`Building... ${elapsed}s`);
            }
        }

        if (!deployed) {
            throw new Error('Initial deployment timed out after 3 minutes');
        }

        await page.waitForTimeout(3000);

        // Get deployment URL from page
        const bodyText = await page.textContent('body');
        const urlMatch = bodyText.match(/https:\/\/[^\s]+\.vercel\.app/);
        if (urlMatch) {
            deploymentUrl = urlMatch[0];
            log(`Initial deployment URL: ${deploymentUrl}`);
        }

        // Take screenshot of initial deployment
        await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'customer_test_01_initial.png'), fullPage: true });
        log('Screenshot: Initial deployment saved');

        // Step 5: Send chat amendment
        log('Sending chat amendment...');
        const chatInput = page.locator('textarea').first();
        await chatInput.fill('Add a phone number 555-PIZZA-NOW (555-749-9266) at the very top in large bold text');
        
        // Click send/submit for modification
        const sendBtn = page.locator('button svg[class*="send"], button:has-text("Send")').first();
        if (await sendBtn.isVisible().catch(() => false)) {
            await sendBtn.click();
        } else {
            await page.keyboard.press('Enter');
        }
        log('Amendment request sent');

        // Step 6: Wait for preview to update with NEW deployment URL
        log('Waiting for amendment deployment...');
        await page.waitForTimeout(2000);

        // Check for "Applying changes" message
        const applyingVisible = await page.locator('text=Applying').isVisible().catch(() => false);
        if (applyingVisible) {
            log('Saw "Applying changes" message - good!');
        }

        // Wait for new deployment
        let newUrl = null;
        const amendStart = Date.now();
        const amendMaxWait = 120000; // 2 minutes for amendment

        while (!newUrl && Date.now() - amendStart < amendMaxWait) {
            await page.waitForTimeout(3000);
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
        await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'customer_test_02_amendment.png'), fullPage: true });
        log('Screenshot: Amendment result saved');

        // Verify the amendment worked
        if (newUrl && newUrl !== deploymentUrl) {
            log('=== TEST PASSED ===');
            log('Race condition fix VERIFIED: New URL received after amendment');
            
            // Check deployed site for phone number
            const browser2 = await chromium.launch({ headless: true });
            const page2 = await browser2.newPage();
            await page2.goto(newUrl, { waitUntil: 'networkidle', timeout: 30000 });
            const content = await page2.textContent('body');
            
            if (content.includes('555') || content.includes('PIZZA')) {
                log('Phone number appears in deployed site!');
            }
            
            await page2.screenshot({ path: path.join(ARTIFACTS_DIR, 'customer_test_03_deployed_amended.png'), fullPage: true });
            await browser2.close();
            
            return { success: true, oldUrl: deploymentUrl, newUrl: newUrl };
        } else {
            log('=== TEST FAILED ===');
            log('URL did not change after amendment - race condition may still exist');
            return { success: false, oldUrl: deploymentUrl, newUrl: null };
        }

    } catch (e) {
        log(`ERROR: ${e.message}`);
        await page.screenshot({ path: path.join(ARTIFACTS_DIR, 'customer_test_error.png') }).catch(() => {});
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
