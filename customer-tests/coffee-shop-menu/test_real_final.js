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
    log("=== REAL FINAL TEST - Chat Amendment with Deployed Verification ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

        // Build initial page
        log("Building initial page...");
        const textarea = await page.locator("textarea").first();
        await textarea.fill("Bean & Brew coffee shop landing. Brown/cream colors (bg-amber-900 header, bg-amber-50 sections). Hero with tagline. Footer says just: Built with Faibric");

        await page.locator("button:has-text(\"Start Building\")").first().click();
        await waitForBuild(page, 180000);
        await page.waitForTimeout(5000);

        // Get initial deployment URL
        const pageText = await page.textContent("body");
        const urlMatch = pageText.match(/https:\/\/[^\s]+\.vercel\.app/);
        const initialUrl = urlMatch ? urlMatch[0] : null;
        log("Initial URL: " + initialUrl);

        // Screenshot deployed site BEFORE
        if (initialUrl) {
            const page2 = await browser.newPage();
            page2.setViewportSize({ width: 1280, height: 900 });
            await page2.goto(initialUrl, { waitUntil: "networkidle", timeout: 30000 });
            await page2.waitForTimeout(2000);
            await page2.screenshot({ path: path.join(SCREENSHOTS_DIR, "real-01-DEPLOYED-BEFORE.png"), fullPage: true });
            log("Screenshot: DEPLOYED site BEFORE amendment");
            await page2.close();
        }

        // Send amendment
        log("Sending chat amendment: Add phone number...");
        const chatInput = await page.locator("input[type=text]").first();
        await chatInput.fill("Add our phone number CALL US: (555) BREW-NOW in the footer, make it big and prominent");
        await chatInput.press("Enter");
        log("Amendment sent");

        // Wait for modification and redeployment
        log("Waiting 45s for modification and deployment...");
        await page.waitForTimeout(45000);

        // Screenshot builder showing chat
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "real-02-BUILDER-AFTER.png"), fullPage: true });
        log("Screenshot: Builder after amendment");

        // Screenshot deployed site AFTER
        if (initialUrl) {
            log("Checking deployed site for phone number...");
            const page3 = await browser.newPage();
            page3.setViewportSize({ width: 1280, height: 900 });
            // Add cache-busting
            await page3.goto(initialUrl + "?t=" + Date.now(), { waitUntil: "networkidle", timeout: 30000 });
            await page3.waitForTimeout(3000);
            
            const content = await page3.content();
            const hasPhone = content.includes("555") || content.includes("BREW-NOW");
            log("Phone number in deployed site: " + hasPhone);
            
            await page3.screenshot({ path: path.join(SCREENSHOTS_DIR, "real-03-DEPLOYED-AFTER.png"), fullPage: true });
            log("Screenshot: DEPLOYED site AFTER amendment");
            await page3.close();
        }

        log("=== TEST COMPLETE ===");
        await browser.close();

    } catch (e) {
        log("ERROR: " + e.message);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "real-error.png") }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
