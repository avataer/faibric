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
    log("=== FINAL PROOF TEST ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1600, height: 1000 });

    try {
        await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

        log("Building initial page...");
        const textarea = await page.locator("textarea").first();
        await textarea.fill("Bean & Brew coffee shop. Brown/cream colors. Hero section. Footer says only: Built with Faibric. NO phone numbers.");

        await page.locator("button:has-text(\"Start Building\")").first().click();
        await waitForBuild(page, 180000);
        await page.waitForTimeout(5000);
        
        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "FINAL-01-BEFORE.png"), fullPage: true });
        log("BEFORE screenshot taken");

        // Send amendment
        log("Sending amendment...");
        const chatInput = await page.locator("input[type=text]").first();
        await chatInput.fill("Add phone: CALL US (555) BREW-NOW in the footer, make it prominent with dark background");
        await chatInput.press("Enter");

        // Wait for modification AND deployment
        log("Waiting 90s for full modification cycle...");
        await page.waitForTimeout(90000);

        // Try to click refresh multiple times
        for (let i = 0; i < 3; i++) {
            const refreshBtn = await page.locator("button").filter({ hasText: /refresh/i }).first();
            if (await refreshBtn.isVisible().catch(() => false)) {
                await refreshBtn.click();
                log("Clicked refresh " + (i+1));
                await page.waitForTimeout(5000);
            }
        }

        // Also try clicking the preview area to force reload
        await page.keyboard.press("F5");
        await page.waitForTimeout(3000);

        await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "FINAL-02-AFTER.png"), fullPage: true });
        log("AFTER screenshot taken");

        // Get the new deployment URL and screenshot it directly
        const pageText = await page.textContent("body");
        const urls = pageText.match(/https:\/\/app[a-z0-9]+-[a-z0-9]+-antons-projects[^\s]*/g);
        if (urls && urls.length > 0) {
            const latestUrl = urls[urls.length - 1];
            log("Opening deployed URL: " + latestUrl);
            
            const page2 = await browser.newPage();
            page2.setViewportSize({ width: 1280, height: 900 });
            await page2.goto(latestUrl, { waitUntil: "networkidle", timeout: 30000 });
            await page2.waitForTimeout(3000);
            
            const hasPhone = (await page2.content()).includes("555");
            log("Deployed site has phone: " + hasPhone);
            
            await page2.screenshot({ path: path.join(SCREENSHOTS_DIR, "FINAL-03-DEPLOYED.png"), fullPage: true });
            log("Deployed screenshot taken");
            await page2.close();
        }

        log("=== TEST COMPLETE ===");
        await browser.close();

    } catch (e) {
        log("ERROR: " + e.message);
        await browser.close();
        throw e;
    }
}

run().then(() => process.exit(0)).catch(() => process.exit(1));
