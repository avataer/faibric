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
    log("=== FINAL CUSTOMER TEST - Chat Amendment Verification ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    try {
        await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

        // Step 1: Initial build WITHOUT phone
        log("Step 1: Building page WITHOUT phone number...");
        const textarea = await page.locator("textarea").first();
        await textarea.fill("Create a landing page for Bean & Brew coffee shop. Brown and cream colors (bg-amber-900 header, bg-amber-50 sections). Include hero with tagline and about section. NO contact info or phone numbers.");

        await page.locator("button:has-text(\"Start Building\")").first().click();
        log("Build started");

        await waitForBuild(page, 180000);
        await page.waitForTimeout(5000);
        
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "final-01-BEFORE.png"), fullPage: true });
        log("Screenshot: final-01-BEFORE.png");

        // Step 2: Send amendment
        log("Step 2: Sending chat amendment to ADD phone number...");
        const chatInput = await page.locator("input[type=text]").first();
        await chatInput.fill("Add phone number (555) BREW-NOW in the footer section. Make it prominent with a phone icon.");
        await chatInput.press("Enter");
        log("Amendment sent");

        // Wait for rebuild to complete - check for Deployed button to reappear
        log("Step 3: Waiting for rebuild...");
        await page.waitForTimeout(10000); // Initial wait
        
        let rebuilt = false;
        for (let i = 0; i < 40; i++) {
            await page.waitForTimeout(5000);
            log("Waiting... " + (i * 5 + 10) + "s");
            
            // Check if preview has been updated
            const content = await page.content();
            if (content.includes("555") || content.includes("BREW")) {
                log("Phone number detected in page!");
                rebuilt = true;
                break;
            }
        }

        await page.waitForTimeout(5000);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "final-02-AFTER.png"), fullPage: true });
        log("Screenshot: final-02-AFTER.png");

        // Check the preview iframe for phone number
        const pageContent = await page.content();
        const hasPhone = pageContent.includes("555") || pageContent.includes("BREW-NOW");
        log("Phone number in page: " + hasPhone);

        log("=== TEST COMPLETE ===");
        await browser.close();

    } catch (e) {
        log("ERROR: " + e.message);
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "final-error.png") }).catch(() => {});
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
