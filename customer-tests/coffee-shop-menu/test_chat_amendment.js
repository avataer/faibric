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

async function run() {
    log("=== CHAT AMENDMENT TEST - VISIBLE CHANGE ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        // Go to builder - it should show existing project
        await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });
        await page.waitForTimeout(3000);

        // Screenshot BEFORE - current state
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amendment-01-before.png"), fullPage: true });
        log("Screenshot: amendment-01-before.png - Current state");

        // Find the chat input and send amendment
        log("Sending chat amendment: Add phone number to footer...");
        const chatInput = await page.locator("input[type=\"text\"]:not([disabled])").first();
        await chatInput.fill("Add a phone number 555-COFFEE prominently in the footer section. Make it visible and styled nicely.");
        await chatInput.press("Enter");
        log("Amendment sent");

        // Wait for rebuild
        log("Waiting for rebuild...");
        await page.waitForTimeout(90000);

        // Screenshot AFTER - should show phone number in footer
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amendment-02-after.png"), fullPage: true });
        log("Screenshot: amendment-02-after.png - After amendment");

        // Scroll to footer to capture it clearly
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(2000);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amendment-03-footer-detail.png"), fullPage: true });
        log("Screenshot: amendment-03-footer-detail.png - Footer detail");

        log("=== CHAT AMENDMENT TEST COMPLETE ===");
        await browser.close();

    } catch (e) {
        log(`ERROR: ${e.message}`);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amendment-error.png") }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
