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

async function waitForBuild(page, maxWaitMs) {
    const startTime = Date.now();
    while (Date.now() - startTime < maxWaitMs) {
        const deployed = await page.locator("button:has-text(\"Deployed\")").first();
        if (await deployed.isVisible().catch(() => false)) return true;
        await page.waitForTimeout(3000);
        log("Building... " + Math.round((Date.now() - startTime) / 1000) + "s");
    }
    return false;
}

async function run() {
    log("=== VISIBLE AMENDMENT TEST - Phone Number Addition ===");

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

        // Step 1: Initial build - simple landing page WITHOUT phone number
        log("Step 1: Building initial page (no phone number)...");
        const textarea = await page.locator("textarea").first();
        await textarea.fill("Create a simple landing page for Bean & Brew coffee shop with brown and cream colors. Include a hero section with tagline and an about section. Use bg-amber-900 for header and bg-amber-50 for sections. Do NOT include any contact information or phone numbers yet.");

        await page.locator("button:has-text(\"Start Building\")").first().click();
        log("Build started");

        await waitForBuild(page, 180000);
        await page.waitForTimeout(5000);
        
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "visible-01-BEFORE.png"), fullPage: true });
        log("Screenshot: visible-01-BEFORE.png - Initial build WITHOUT phone number");

        // Step 2: Send amendment to ADD phone number
        log("Step 2: Sending amendment to ADD phone number...");
        const chatInput = await page.locator("input[type=text]").first();
        await chatInput.fill("Add our phone number (555) BREW-123 prominently in the footer. Make it large and easy to see with a phone icon next to it.");
        await chatInput.press("Enter");
        log("Amendment sent - requesting phone number addition");

        // Wait for rebuild
        log("Step 3: Waiting for rebuild with phone number...");
        await page.waitForTimeout(120000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "visible-02-AFTER.png"), fullPage: true });
        log("Screenshot: visible-02-AFTER.png - After amendment WITH phone number");

        log("=== TEST COMPLETE - Compare screenshots to see phone number added ===");
        await browser.close();

    } catch (e) {
        log("ERROR: " + e.message);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "visible-error.png") }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
