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
    log('=== COFFEE SHOP v5 - STRICT COLOR ENFORCEMENT ===');

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });

        // Start fresh
        const startNew = await page.locator('button:has-text("Start New")').first();
        if (await startNew.isVisible().catch(() => false)) {
            await startNew.click();
            await page.waitForTimeout(2000);
        }

        log('Submitting with STRICT BROWN/CREAM requirement...');
        const textarea = await page.locator('textarea').first();
        await textarea.fill(`Create a digital menu for "Bean & Brew" coffee shop.

MANDATORY COLOR SCHEME - READ CAREFULLY:
1. Header/Navbar: bg-amber-900 (dark coffee brown)
2. ALL section backgrounds: bg-amber-50 (cream/beige) - NOT white, NOT gray
3. Buttons: bg-amber-700
4. Cards: bg-amber-50 with border-amber-200

FORBIDDEN COLORS - DO NOT USE:
- NO gray (bg-gray-*)
- NO slate (bg-slate-*)
- NO blue (bg-blue-*, bg-indigo-*)
- NO green (bg-green-*, bg-emerald-*)
- NO white backgrounds

ONLY USE: amber, orange, yellow, stone color families

IMAGES: Use coffee-themed Picsum seeds like coffee-latte, espresso-cup, cafe-interior

Content: Coffee menu with espresso drinks, lattes, cappuccinos. Daily specials. About us.`);

        await page.locator('button:has-text("Start Building")').first().click();
        log('Build started');

        await waitForBuild(page, 180000);
        await page.waitForTimeout(5000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'v5-01-initial.png'), fullPage: true });
        log('Screenshot: Initial build');

        // Send amendment with explicit colors
        log('Sending explicit color amendment...');
        const input = await page.locator('input[type="text"]:not([disabled])').first();
        await input.fill('CRITICAL: Replace ALL bg-gray with bg-amber-50. Replace ALL bg-blue with bg-amber-700. Header must be bg-amber-900. Section backgrounds must be bg-amber-50 (cream). NO GRAY, NO BLUE, NO GREEN anywhere.');
        await input.press('Enter');

        log('Waiting for rebuild...');
        await page.waitForTimeout(90000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'v5-02-amendment.png'), fullPage: true });
        log('Screenshot: After amendment');

        // Get URL
        const text = await page.textContent('body');
        const match = text.match(/https:\/\/[^\s]+\.vercel\.app/);
        const url = match ? match[0] : null;

        await browser.close();

        if (url) {
            log(`Deployment URL: ${url}`);
            fs.writeFileSync(path.join(TEST_DIR, 'deployment_url_v5.txt'), url);

            // Capture deployed site
            log('Capturing deployed site...');
            const browser2 = await chromium.launch({ headless: true });
            const page2 = await browser2.newPage();
            page2.setViewportSize({ width: 1280, height: 900 });

            await new Promise(r => setTimeout(r, 5000));
            await page2.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
            await page2.waitForTimeout(3000);

            await page2.screenshot({ path: path.join(SCREENSHOTS_DIR, 'v5-03-deployed.png'), fullPage: true });
            log('Screenshot: Deployed site');

            await browser2.close();
        }

        log('=== TEST v5 COMPLETE ===');
        return { success: true, url };

    } catch (e) {
        log(`ERROR: ${e.message}`);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'v5-error.png') }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
