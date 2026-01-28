const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const SCREENSHOTS_DIR = "/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu/screenshots";

function log(msg) { console.log("[" + new Date().toISOString() + "] " + msg); }

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
    log("=== VISIBLE AREA TEST ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1600, height: 1000 });

    await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

    log("Building simple page...");
    const textarea = await page.locator("textarea").first();
    await textarea.fill("Bean & Brew coffee shop. Single section only - just a hero with tagline. Brown/cream colors. Keep it minimal.");

    await page.locator("button:has-text(\"Start Building\")").first().click();
    await waitForBuild(page, 180000);
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "VISIBLE-01-BEFORE.png"), fullPage: true });
    log("BEFORE screenshot");

    log("Amendment: Add phone to HERO section...");
    const chatInput = await page.locator("input[type=text]").first();
    await chatInput.fill("Add a big prominent phone number CALL: (555) BREW-NOW right below the tagline in the hero section. Make it large white text.");
    await chatInput.press("Enter");

    log("Waiting 70s for modification...");
    await page.waitForTimeout(70000);

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "VISIBLE-02-AFTER.png"), fullPage: true });
    log("AFTER screenshot");

    await browser.close();
    log("=== DONE ===");
}

run().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
