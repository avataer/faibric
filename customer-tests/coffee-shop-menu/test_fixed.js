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
    log("=== FIXED PREVIEW TEST ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1600, height: 1000 });

    await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

    log("Building initial page...");
    const textarea = await page.locator("textarea").first();
    await textarea.fill("Simple Bean & Brew page. Brown/cream colors. Just hero section. Footer: Built with Faibric. NO phone.");

    await page.locator("button:has-text(\"Start Building\")").first().click();
    await waitForBuild(page, 180000);
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "FIXED-01-BEFORE.png"), fullPage: true });
    log("BEFORE screenshot");

    log("Sending amendment...");
    const chatInput = await page.locator("input[type=text]").first();
    await chatInput.fill("Add CALL US: (555) BREW-NOW in footer with dark brown background");
    await chatInput.press("Enter");

    // Wait for modification AND deployment to complete
    log("Waiting for modification...");
    let foundPhone = false;
    for (let i = 0; i < 30; i++) {
        await page.waitForTimeout(5000);
        
        // Check if phone number appears in preview iframe
        const frames = page.frames();
        for (const frame of frames) {
            try {
                const content = await frame.content();
                if (content.includes("555") || content.includes("BREW-NOW")) {
                    log("Phone number found in preview at " + (i * 5) + "s!");
                    foundPhone = true;
                    break;
                }
            } catch {}
        }
        
        if (foundPhone) break;
        log("Waiting... " + (i * 5) + "s");
    }

    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "FIXED-02-AFTER.png"), fullPage: true });
    log("AFTER screenshot - Phone in preview: " + foundPhone);

    await browser.close();
    log("=== DONE ===");
}

run().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
