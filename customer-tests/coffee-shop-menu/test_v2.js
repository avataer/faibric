/**
 * Coffee Shop Menu - Customer Test v2
 * RETRY with STRONGER color requirements and LONGER waits
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TEST_DIR = '/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu';
const SCREENSHOTS_DIR = path.join(TEST_DIR, 'screenshots');

function log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}`;
    console.log(logMessage);
    fs.appendFileSync(path.join(TEST_DIR, 'playwright_v2.log'), logMessage + '\n');
    fs.appendFileSync(path.join(TEST_DIR, 'FULL_TEST_LOG.md'), `- ${logMessage}\n`);
}

async function waitForBuildComplete(page, maxWaitMs = 180000) {
    log('Waiting for build to complete...');
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitMs) {
        const deployedBadge = await page.locator('button:has-text("Deployed"), span:has-text("Deployed")').first();
        if (await deployedBadge.isVisible().catch(() => false)) {
            log('Build complete - Deployed badge visible');
            return true;
        }

        const enabledInput = await page.locator('input[placeholder*="Describe changes"]:not([disabled])').first();
        if (await enabledInput.isVisible().catch(() => false)) {
            log('Build complete - Input field enabled');
            return true;
        }

        await page.waitForTimeout(3000);
        const elapsed = Math.round((Date.now() - startTime) / 1000);
        log(`Still building... ${elapsed}s elapsed`);
    }

    return false;
}

async function waitForRebuildWithChanges(page, maxWaitMs = 120000) {
    log('Waiting for rebuild with color changes...');
    const startTime = Date.now();

    // First wait for "Applying changes" or rebuilding indicator
    await page.waitForTimeout(3000);

    // Then wait for build to complete again
    while (Date.now() - startTime < maxWaitMs) {
        // Check for "AI modifying" or "Applying changes" to finish
        const applyingText = await page.locator('text=/applying|modifying|rebuilding/i').first();
        const isApplying = await applyingText.isVisible().catch(() => false);

        if (!isApplying) {
            // Check if deployed badge is back
            const deployedBadge = await page.locator('button:has-text("Deployed")').first();
            if (await deployedBadge.isVisible().catch(() => false)) {
                log('Rebuild complete - Deployed badge visible');
                // Wait extra time for preview to update
                await page.waitForTimeout(5000);
                return true;
            }
        }

        await page.waitForTimeout(3000);
        const elapsed = Math.round((Date.now() - startTime) / 1000);
        log(`Rebuild in progress... ${elapsed}s elapsed`);
    }

    return false;
}

async function runTest() {
    log('========================================');
    log('COFFEE SHOP MENU v2 - STRONGER COLORS');
    log('========================================');

    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1400, height: 900 }
    });

    const page = await context.newPage();

    try {
        log('STEP 1: Navigating to Faibric...');
        await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
        await page.waitForTimeout(2000);

        // Click "Start New" if visible (to start fresh)
        const startNewBtn = await page.locator('button:has-text("Start New")').first();
        if (await startNewBtn.isVisible().catch(() => false)) {
            await startNewBtn.click();
            log('Clicked Start New to begin fresh build');
            await page.waitForTimeout(2000);
        }

        log('STEP 2: Submitting request with STRONG color requirement...');
        const textarea = await page.locator('textarea').first();
        await textarea.waitFor({ state: 'visible', timeout: 10000 });

        // MUCH STRONGER color requirement
        const initialRequest = `Create a digital menu for "Bean & Brew" coffee shop.

CRITICAL COLOR REQUIREMENT - THIS IS MANDATORY:
- Background color: #8B4513 (saddle brown) or #A0522D (sienna) - DARK BROWN
- Secondary backgrounds: #F5DEB3 (wheat) or #DEB887 (burlywood) - CREAM/BEIGE
- Headers and buttons: Dark espresso brown (#3E2723 or #4E342E)
- Text on dark backgrounds: Cream colored (#FFF8DC or #FAEBD7)

The entire site MUST look like a warm, cozy coffee shop with BROWN and CREAM colors.
NO GRAY. NO WHITE BACKGROUNDS. ONLY BROWN AND CREAM.

Content:
- Menu with espresso drinks, lattes, cappuccinos, cold brew
- Prices for each item
- Daily specials section
- About/Our Story section

Make the header DARK BROWN. Make section backgrounds CREAM/BEIGE. This is non-negotiable.`;

        await textarea.fill(initialRequest);
        log('Filled request with strong color requirements');
        await page.waitForTimeout(500);

        const buildButton = await page.locator('button:has-text("Start Building")').first();
        await buildButton.click();
        log('Clicked Start Building');

        log('STEP 3: Waiting for initial build...');
        await waitForBuildComplete(page, 180000);

        await page.waitForTimeout(5000);
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, 'v2-01-initial-build.png'),
            fullPage: true
        });
        log('Screenshot: Initial build');

        log('STEP 4: Sending color amendment...');
        await page.waitForTimeout(2000);

        const chatInput = await page.locator('input[type="text"]:not([disabled])').first();
        await chatInput.waitFor({ state: 'visible', timeout: 10000 });

        const amendmentRequest = `URGENT COLOR FIX NEEDED:
The colors are WRONG. I specifically need:
1. DARK BROWN header (hex #4E342E or similar espresso color)
2. CREAM/BEIGE backgrounds (hex #F5DEB3 or #DEB887)
3. NO GRAY colors anywhere
4. The site should feel WARM like a coffee shop

Please change the header to dark brown and all section backgrounds to cream/beige. This is the customer's #1 requirement.`;

        await chatInput.fill(amendmentRequest);
        log('Filled color amendment');
        await chatInput.press('Enter');
        log('Sent amendment');

        log('STEP 5: Waiting for rebuild with colors...');
        await waitForRebuildWithChanges(page, 120000);

        // Wait extra time for preview to fully update
        await page.waitForTimeout(10000);

        // CRITICAL SCREENSHOT: Must show chat + brown/cream preview
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, 'v2-02-chat-with-brown-preview.png'),
            fullPage: true
        });
        log('CRITICAL SCREENSHOT: Chat with color amendment + preview');

        // Get deployment URL
        const pageText = await page.textContent('body');
        const urlMatch = pageText.match(/https:\/\/[^\s]+\.vercel\.app/);
        const deploymentUrl = urlMatch ? urlMatch[0] : null;

        if (deploymentUrl) {
            log(`Deployment URL: ${deploymentUrl}`);
            fs.writeFileSync(path.join(TEST_DIR, 'deployment_url_v2.txt'), deploymentUrl);

            // Close first browser
            await browser.close();

            // Capture deployed site
            log('STEP 6: Capturing deployed site...');
            await new Promise(r => setTimeout(r, 5000));

            const browser2 = await chromium.launch({ headless: true });
            const page2 = await browser2.newPage();
            page2.setViewportSize({ width: 1280, height: 900 });

            await page2.goto(deploymentUrl, { waitUntil: 'networkidle', timeout: 30000 });
            await page2.waitForTimeout(3000);

            await page2.screenshot({
                path: path.join(SCREENSHOTS_DIR, 'v2-03-deployed-site.png'),
                fullPage: true
            });
            log('Screenshot: Deployed site');

            await browser2.close();
        } else {
            log('WARNING: No deployment URL found');
            await browser.close();
        }

        log('========================================');
        log('TEST v2 COMPLETED');
        log('========================================');

        return { success: true, deploymentUrl };

    } catch (error) {
        log(`ERROR: ${error.message}`);
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, 'v2-error.png'),
            fullPage: true
        }).catch(() => {});
        await browser.close();
        throw error;
    }
}

runTest()
    .then((result) => {
        log('Test finished');
        process.exit(0);
    })
    .catch((error) => {
        log(`Test failed: ${error.message}`);
        process.exit(1);
    });
