const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const TEST_DIR = '/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu';
const SCREENSHOTS_DIR = path.join(TEST_DIR, 'screenshots');

function log(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
    fs.appendFileSync(path.join(TEST_DIR, 'FULL_TEST_LOG.md'), `- [${timestamp}] ${message}\n`);
}

async function waitForBuild(page, maxWaitMs = 180000) {
    const startTime = Date.now();
    while (Date.now() - startTime < maxWaitMs) {
        const deployed = await page.locator('button:has-text("Deployed")').first();
        if (await deployed.isVisible().catch(() => false)) return true;
        await page.waitForTimeout(3000);
        log(`Building... ${Math.round((Date.now() - startTime) / 1000)}s`);
    }
    return false;
}

async function run() {
    log('=== COFFEE SHOP v7 - VERCEL COLOR ENFORCEMENT FIX ===');

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });

        const startNew = await page.locator('button:has-text("Start New")').first();
        if (await startNew.isVisible().catch(() => false)) {
            await startNew.click();
            await page.waitForTimeout(2000);
        }

        log('Submitting with COFFEE BROWN CREAM requirement...');
        const textarea = await page.locator('textarea').first();
        await textarea.fill(`Create a coffee shop menu for "Bean & Brew".

I want a coffee brown and cream color scheme.

Use these exact colors:
- Header: dark brown background (bg-amber-900)
- Sections: cream background (bg-amber-50)
- Buttons: brown (bg-amber-700)

Content: Coffee drinks menu with espresso, latte, cappuccino and prices.`);

        await page.locator('button:has-text("Start Building")').first().click();
        log('Build started');

        await waitForBuild(page, 180000);
        await page.waitForTimeout(5000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'v7-01-initial.png'), fullPage: true });
        log('Screenshot: Initial build');

        const text = await page.textContent('body');
        const match = text.match(/https:\/\/[^\s]+\.vercel\.app/);
        const url = match ? match[0] : null;

        await browser.close();

        if (url) {
            log(`Deployment URL: ${url}`);
            fs.writeFileSync(path.join(TEST_DIR, 'deployment_url_v7.txt'), url);

            log('Capturing deployed site...');
            const browser2 = await chromium.launch({ headless: true });
            const page2 = await browser2.newPage();
            page2.setViewportSize({ width: 1280, height: 900 });

            await new Promise(r => setTimeout(r, 5000));
            await page2.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
            await page2.waitForTimeout(3000);

            await page2.screenshot({ path: path.join(SCREENSHOTS_DIR, 'v7-02-deployed.png'), fullPage: true });
            log('Screenshot: Deployed site');

            await browser2.close();
        }

        log('=== TEST v7 COMPLETE ===');
        return { success: true, url };

    } catch (e) {
        log(`ERROR: ${e.message}`);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'v7-error.png') }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
