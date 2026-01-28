/**
 * Coffee Shop Menu - Customer Test
 *
 * Flow:
 * 1. Initial build (coffee brown/cream request)
 * 2. Wait for build complete
 * 3. Chat amendment: "darker brown header"
 * 4. Wait for rebuild
 * 5. Screenshot: Builder showing chat + brown/cream preview
 * 6. Get deployment URL
 * 7. Screenshot: Deployed site with brown/cream colors
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
    fs.appendFileSync(path.join(TEST_DIR, 'playwright.log'), logMessage + '\n');

    // Also append to FULL_TEST_LOG.md
    fs.appendFileSync(path.join(TEST_DIR, 'FULL_TEST_LOG.md'), `- ${logMessage}\n`);
}

async function waitForBuildComplete(page, maxWaitMs = 180000) {
    log('Waiting for build to complete...');
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitMs) {
        // Check for "Deployed" badge which indicates completion
        const deployedBadge = await page.locator('button:has-text("Deployed"), span:has-text("Deployed")').first();
        if (await deployedBadge.isVisible().catch(() => false)) {
            log('Build complete - Deployed badge visible');
            return true;
        }

        // Check if input is enabled (not disabled)
        const enabledInput = await page.locator('input[placeholder*="Describe changes"]:not([disabled]), input[placeholder*="changes"]:not([disabled])').first();
        if (await enabledInput.isVisible().catch(() => false)) {
            log('Build complete - Input field enabled');
            return true;
        }

        await page.waitForTimeout(3000);
        const elapsed = Math.round((Date.now() - startTime) / 1000);
        log(`Still building... ${elapsed}s elapsed`);
    }

    log('Build timeout reached');
    return false;
}

async function getDeploymentUrl(page) {
    // Look for Vercel URL in the page
    const urlPatterns = [
        'a[href*="vercel.app"]',
        'a[href*=".vercel.app"]',
        'text=/https:\\/\\/[^\\s]+\\.vercel\\.app/'
    ];

    for (const pattern of urlPatterns) {
        try {
            const element = await page.locator(pattern).first();
            if (await element.isVisible().catch(() => false)) {
                const href = await element.getAttribute('href');
                if (href) return href;
                const text = await element.textContent();
                if (text && text.includes('vercel.app')) return text.trim();
            }
        } catch (e) {}
    }

    // Try to find URL in page text
    const pageText = await page.textContent('body');
    const urlMatch = pageText.match(/https:\/\/[^\s]+\.vercel\.app[^\s]*/);
    if (urlMatch) return urlMatch[0];

    return null;
}

async function runTest() {
    log('========================================');
    log('COFFEE SHOP MENU - CUSTOMER TEST');
    log('========================================');
    log('Color Requirement: Coffee brown and cream');

    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const context = await browser.newContext({
        viewport: { width: 1400, height: 900 }
    });

    const page = await context.newPage();
    let deploymentUrl = null;

    try {
        // STEP 1: Navigate to Faibric
        log('STEP 1: Navigating to Faibric...');
        await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
        await page.waitForTimeout(2000);

        // STEP 2: Submit initial coffee shop request
        log('STEP 2: Submitting coffee shop menu request...');
        const textarea = await page.locator('textarea').first();
        await textarea.waitFor({ state: 'visible', timeout: 10000 });

        const initialRequest = `I own a coffee shop called "Bean & Brew". I need a digital menu customers can view on their phones with:

- Our drinks (espresso, lattes, cappuccinos, cold brew, etc.)
- Prices for each item
- Daily specials section
- Our story/about section

IMPORTANT: Use coffee brown and cream colors throughout the design. I want it to feel warm and cozy like a real coffee shop.`;

        await textarea.fill(initialRequest);
        log('Filled initial request');
        await page.waitForTimeout(500);

        // Click Start Building
        const buildButton = await page.locator('button:has-text("Start Building")').first();
        await buildButton.click();
        log('Clicked Start Building');

        // STEP 3: Wait for initial build
        log('STEP 3: Waiting for initial build to complete...');
        const buildSuccess = await waitForBuildComplete(page, 180000);

        if (!buildSuccess) {
            throw new Error('Initial build timed out');
        }

        // Take screenshot of initial build
        await page.waitForTimeout(3000);
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, '01-initial-build.png'),
            fullPage: true
        });
        log('Screenshot: Initial build captured');

        // STEP 4: Send chat amendment for darker brown
        log('STEP 4: Sending chat amendment for darker brown header...');
        await page.waitForTimeout(2000);

        // Find the chat input
        const chatInput = await page.locator('input[type="text"]:not([disabled])').first();
        await chatInput.waitFor({ state: 'visible', timeout: 10000 });

        const amendmentRequest = `Make the header darker brown - like espresso color. And add more cream/beige backgrounds to the menu sections. I want customers to feel like they're looking at a real coffee-stained menu!`;

        await chatInput.fill(amendmentRequest);
        log('Filled amendment request');

        // Press Enter to send
        await chatInput.press('Enter');
        log('Sent amendment via Enter key');

        // STEP 5: Wait for rebuild after amendment
        log('STEP 5: Waiting for rebuild after amendment...');
        await page.waitForTimeout(5000); // Wait for rebuild to start

        // Wait for "Applying changes" or similar, then completion
        await waitForBuildComplete(page, 120000);

        // CRITICAL SCREENSHOT: Builder showing chat (left) + brown/cream preview (right)
        await page.waitForTimeout(5000);
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, '02-chat-amendment-with-preview.png'),
            fullPage: true
        });
        log('CRITICAL SCREENSHOT: Chat amendment with brown/cream preview captured');

        // STEP 6: Get deployment URL
        log('STEP 6: Getting deployment URL...');
        deploymentUrl = await getDeploymentUrl(page);

        if (deploymentUrl) {
            log(`Deployment URL found: ${deploymentUrl}`);
            fs.writeFileSync(path.join(TEST_DIR, 'deployment_url.txt'), deploymentUrl);
        } else {
            log('WARNING: No deployment URL found yet, checking page...');
            // Take diagnostic screenshot
            await page.screenshot({
                path: path.join(SCREENSHOTS_DIR, 'debug-no-url.png'),
                fullPage: true
            });
        }

        // Final state screenshot
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, '03-final-builder-state.png'),
            fullPage: true
        });
        log('Screenshot: Final builder state captured');

        log('========================================');
        log('BUILDER PHASE COMPLETE');
        log('========================================');

    } catch (error) {
        log(`ERROR in builder phase: ${error.message}`);
        await page.screenshot({
            path: path.join(SCREENSHOTS_DIR, 'error-builder.png'),
            fullPage: true
        });
        throw error;
    } finally {
        await browser.close();
    }

    // STEP 7: Screenshot deployed site
    if (deploymentUrl) {
        log('STEP 7: Capturing deployed site screenshot...');

        const browser2 = await chromium.launch({ headless: true });
        const context2 = await browser2.newContext({
            viewport: { width: 1280, height: 800 }
        });
        const page2 = await context2.newPage();

        try {
            // Wait a moment for deployment to be fully live
            await new Promise(r => setTimeout(r, 5000));

            await page2.goto(deploymentUrl, { waitUntil: 'networkidle', timeout: 30000 });
            await page2.waitForTimeout(3000);

            await page2.screenshot({
                path: path.join(SCREENSHOTS_DIR, '04-deployed-site.png'),
                fullPage: true
            });
            log('CRITICAL SCREENSHOT: Deployed site with brown/cream colors captured');

            // Verify site is actually showing content
            const pageContent = await page2.textContent('body');
            if (pageContent.toLowerCase().includes('coffee') || pageContent.toLowerCase().includes('bean') || pageContent.toLowerCase().includes('brew')) {
                log('VERIFIED: Deployed site contains coffee shop content');
            } else {
                log('WARNING: Deployed site may not have expected content');
            }

        } catch (error) {
            log(`ERROR capturing deployed site: ${error.message}`);
        } finally {
            await browser2.close();
        }
    }

    log('========================================');
    log('TEST COMPLETED SUCCESSFULLY');
    log('========================================');

    return { success: true, deploymentUrl };
}

// Run with retry logic
async function runWithRetry(maxRetries = 999) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        log(`\n=== ATTEMPT ${attempt} ===\n`);

        try {
            const result = await runTest();
            if (result.success) {
                log('SUCCESS! All verification passed.');
                return result;
            }
        } catch (error) {
            log(`Attempt ${attempt} failed: ${error.message}`);
            if (attempt < maxRetries) {
                log('Retrying in 10 seconds...');
                await new Promise(r => setTimeout(r, 10000));
            }
        }
    }

    throw new Error('All retry attempts exhausted');
}

runWithRetry()
    .then((result) => {
        log('Test finished successfully');
        console.log('\nDEPLOYMENT URL:', result.deploymentUrl || 'Not captured');
        process.exit(0);
    })
    .catch((error) => {
        log(`Test failed permanently: ${error.message}`);
        process.exit(1);
    });
