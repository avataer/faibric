const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const TEST_DIR = "/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu";
const SCREENSHOTS_DIR = path.join(TEST_DIR, "screenshots");

function log(message) {
    const timestamp = new Date().toISOString();
    console.log("[" + timestamp + "] " + message);
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
    log("=== PROOF TEST - Builder with Chat Visible ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1600, height: 1000 });

    try {
        await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

        // Build initial page - explicitly NO phone
        log("Building initial page WITHOUT phone...");
        const textarea = await page.locator("textarea").first();
        await textarea.fill("Bean & Brew coffee landing page. Brown header (bg-amber-900), cream sections (bg-amber-50). Hero with tagline. Simple footer that just says: Built with Faibric. DO NOT include any phone numbers or contact info.");

        await page.locator("button:has-text(\"Start Building\")").first().click();
        await waitForBuild(page, 180000);
        await page.waitForTimeout(8000);

        // Screenshot builder BEFORE amendment - shows chat + preview without phone
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "REAL-PROOF-01-BEFORE.png"), fullPage: true });
        log("Screenshot: Builder BEFORE amendment (no phone in preview)");

        // Send amendment requesting phone number
        log("Sending chat amendment: Add phone number...");
        const chatInput = await page.locator("input[type=text]").first();
        await chatInput.fill("Add a big phone number section in the footer: CALL US: (555) BREW-NOW");
        await chatInput.press("Enter");
        log("Amendment sent");

        // Wait for modification to complete
        log("Waiting 60s for AI modification and redeployment...");
        await page.waitForTimeout(60000);

        // Refresh the preview iframe
        const refreshBtn = await page.locator("button:has-text(\"Refresh\")").first();
        if (await refreshBtn.isVisible().catch(() => false)) {
            await refreshBtn.click();
            log("Clicked refresh");
            await page.waitForTimeout(5000);
        }

        // Screenshot builder AFTER amendment - shows chat with request + preview with phone
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "REAL-PROOF-02-AFTER.png"), fullPage: true });
        log("Screenshot: Builder AFTER amendment (chat + preview with phone)");

        log("=== TEST COMPLETE ===");
        await browser.close();

    } catch (e) {
        log("ERROR: " + e.message);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "proof-error.png") }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
