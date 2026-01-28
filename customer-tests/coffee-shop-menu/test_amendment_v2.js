const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const TEST_DIR = "/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu";
const SCREENSHOTS_DIR = path.join(TEST_DIR, "screenshots");

function log(message) {
    const timestamp = new Date().toISOString();
    console.log("[" + timestamp + "] " + message);
    fs.appendFileSync(path.join(TEST_DIR, "FULL_TEST_LOG.md"), "- [" + timestamp + "] " + message + "\n");
}

async function run() {
    log("=== CHAT AMENDMENT TEST v2 ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });
        await page.waitForTimeout(5000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amend-v2-01-before.png"), fullPage: true });
        log("Screenshot: before.png");

        // Look for input field
        const chatInput = await page.locator("input").first();
        const isVisible = await chatInput.isVisible().catch(() => false);
        
        if (!isVisible) {
            const html = await page.content();
            fs.writeFileSync(path.join(TEST_DIR, "page_debug.html"), html);
            throw new Error("No input found");
        }

        log("Found input, sending amendment...");
        await chatInput.fill("Add phone number 555-BREW in footer");
        await chatInput.press("Enter");
        log("Sent");

        log("Waiting 90s...");
        await page.waitForTimeout(90000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amend-v2-02-after.png"), fullPage: true });
        log("Screenshot: after.png");
        log("=== DONE ===");

        await browser.close();
    } catch (e) {
        log("ERROR: " + e.message);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amend-v2-error.png") }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
