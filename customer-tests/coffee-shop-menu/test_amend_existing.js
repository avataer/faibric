const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const TEST_DIR = "/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu";
const SCREENSHOTS_DIR = path.join(TEST_DIR, "screenshots");
const PROJECT_ID = 19;

function log(message) {
    const timestamp = new Date().toISOString();
    console.log("[" + timestamp + "] " + message);
    fs.appendFileSync(path.join(TEST_DIR, "FULL_TEST_LOG.md"), "- [" + timestamp + "] " + message + "\n");
}

async function run() {
    log("=== CHAT AMENDMENT TEST - EXISTING PROJECT #" + PROJECT_ID + " ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        // Try to access the project builder directly
        const builderUrl = "http://localhost:5173/builder/" + PROJECT_ID;
        log("Navigating to: " + builderUrl);
        await page.goto(builderUrl, { waitUntil: "networkidle", timeout: 30000 });
        await page.waitForTimeout(5000);

        // Screenshot current state
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amend-exist-01-before.png"), fullPage: true });
        log("Screenshot: before.png");

        // Check URL after navigation
        const currentUrl = page.url();
        log("Current URL: " + currentUrl);

        // Save page content for debugging
        const html = await page.content();
        fs.writeFileSync(path.join(TEST_DIR, "builder_page.html"), html);
        log("Page HTML saved to builder_page.html");

        // Look for any input/textarea
        const inputs = await page.locator("input, textarea").all();
        log("Found " + inputs.length + " input/textarea elements");

        // Try to find chat input
        const chatInput = await page.locator("input[type=text]").first();
        if (await chatInput.isVisible({ timeout: 5000 }).catch(() => false)) {
            log("Found visible text input, sending amendment...");
            await chatInput.fill("Add phone number 555-BREW prominently in the footer");
            await chatInput.press("Enter");
            log("Amendment sent");
            
            log("Waiting 90s for rebuild...");
            await page.waitForTimeout(90000);

            await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amend-exist-02-after.png"), fullPage: true });
            log("Screenshot: after.png");
        } else {
            log("No visible text input found");
        }

        log("=== TEST COMPLETE ===");
        await browser.close();

    } catch (e) {
        log("ERROR: " + e.message);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "amend-exist-error.png") }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
