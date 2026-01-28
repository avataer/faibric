const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const SCREENSHOTS_DIR = "/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu/screenshots";

function log(message) {
    console.log("[" + new Date().toISOString() + "] " + message);
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
    log("=== SCROLL TEST ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1600, height: 1000 });

    await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

    log("Building...");
    const textarea = await page.locator("textarea").first();
    await textarea.fill("Bean & Brew coffee. Brown/cream. Hero section. Footer: Built with Faibric. NO phone.");

    await page.locator("button:has-text(\"Start Building\")").first().click();
    await waitForBuild(page, 180000);
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "SCROLL-01-BEFORE.png"), fullPage: true });
    log("BEFORE");

    log("Amendment...");
    const chatInput = await page.locator("input[type=text]").first();
    await chatInput.fill("Add big phone section in footer: CALL US (555) BREW-NOW with dark brown bg-amber-900 background");
    await chatInput.press("Enter");

    log("Waiting for modification...");
    await page.waitForTimeout(60000);

    // Find the preview iframe and scroll it to the bottom
    const iframe = page.frameLocator("iframe").first();
    try {
        await iframe.locator("body").evaluate(el => el.scrollTo(0, el.scrollHeight));
        log("Scrolled preview to bottom");
    } catch (e) {
        log("Could not scroll iframe: " + e.message);
    }

    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "SCROLL-02-AFTER.png"), fullPage: true });
    log("AFTER - scrolled to show footer");

    await browser.close();
    log("=== DONE ===");
}

run().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
