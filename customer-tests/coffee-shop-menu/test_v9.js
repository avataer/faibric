const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const TEST_DIR = "/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu";
const SCREENSHOTS_DIR = path.join(TEST_DIR, "screenshots");

function log(message) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] ${message}`);
    fs.appendFileSync(path.join(TEST_DIR, "FULL_TEST_LOG.md"), `- [${timestamp}] ${message}\n`);
}

async function waitForBuild(page, maxWaitMs = 180000) {
    const startTime = Date.now();
    while (Date.now() - startTime < maxWaitMs) {
        const deployed = await page.locator("button:has-text(\"Deployed\")").first();
        if (await deployed.isVisible().catch(() => false)) return true;
        await page.waitForTimeout(3000);
        log(`Building... ${Math.round((Date.now() - startTime) / 1000)}s`);
    }
    return false;
}

async function run() {
    log("=== COFFEE SHOP v9 - COMPLETE TEST WITH CHAT ITERATION ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

        const startNew = await page.locator("button:has-text(\"Start New\")").first();
        if (await startNew.isVisible().catch(() => false)) {
            await startNew.click();
            await page.waitForTimeout(2000);
        }

        // STEP 1: Initial simple request
        log("STEP 1: Submitting initial request...");
        const textarea = await page.locator("textarea").first();
        await textarea.fill(`Create a coffee shop menu for "Bean & Brew".
I want cream and brown colors.
Include espresso, latte, cappuccino with prices.`);

        await page.locator("button:has-text(\"Start Building\")").first().click();
        log("Build started");

        await waitForBuild(page, 180000);
        await page.waitForTimeout(5000);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "v9-01-initial.png"), fullPage: true });
        log("Screenshot: v9-01-initial.png - Initial build");

        // STEP 2: Chat amendment - use input[type="text"] not textarea
        log("STEP 2: Sending chat amendment for color changes...");
        const chatInput = await page.locator("input[type=\"text\"]:not([disabled])").first();
        await chatInput.fill("Make all section backgrounds use bg-amber-50 (cream color). The header should be bg-amber-900 (dark brown). NO gray colors anywhere. This is CRITICAL.");
        await chatInput.press("Enter");
        log("Amendment sent via chat input");

        // STEP 3: Wait for rebuild
        log("STEP 3: Waiting for rebuild after amendment...");
        await page.waitForTimeout(90000);

        // STEP 4: Screenshot showing chat + preview
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "v9-02-chat-amendment-with-preview.png"), fullPage: true });
        log("CRITICAL Screenshot: v9-02-chat-amendment-with-preview.png - Chat panel with amendment + preview");

        // STEP 5: Get deployment URL
        const text = await page.textContent("body");
        const match = text.match(/https:\/\/[^\s]+\.vercel\.app/);
        const url = match ? match[0] : null;
        
        if (url) {
            log(`Deployment URL: ${url}`);
            fs.writeFileSync(path.join(TEST_DIR, "deployment_url_v9.txt"), url);
        }

        await browser.close();

        // STEP 6: Capture deployed site
        if (url) {
            log("STEP 6: Capturing deployed site...");
            const browser2 = await chromium.launch({ headless: true });
            const page2 = await browser2.newPage();
            page2.setViewportSize({ width: 1280, height: 900 });

            await new Promise(r => setTimeout(r, 5000));
            await page2.goto(url, { waitUntil: "networkidle", timeout: 30000 });
            await page2.waitForTimeout(3000);

            await page2.screenshot({ path: path.join(SCREENSHOTS_DIR, "v9-03-deployed.png"), fullPage: true });
            log("Screenshot: v9-03-deployed.png - Deployed site");

            await browser2.close();
        }

        log("=== TEST v9 COMPLETE ===");
        return { success: true, url };

    } catch (e) {
        log(`ERROR: ${e.message}`);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "v9-error.png") }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
