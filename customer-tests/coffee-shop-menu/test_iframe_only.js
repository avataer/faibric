const { chromium } = require("playwright");
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
    log("=== IFRAME ONLY TEST ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1600, height: 1000 });

    await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

    log("Building...");
    const textarea = await page.locator("textarea").first();
    await textarea.fill("Simple Bean & Brew. Just hero with title. Brown/cream. Minimal.");

    await page.locator("button:has-text(\"Start Building\")").first().click();
    await waitForBuild(page, 180000);
    await page.waitForTimeout(5000);
    
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "IFRAME-01-BEFORE.png"), fullPage: true });
    log("BEFORE");

    log("Amendment...");
    const chatInput = await page.locator("input[type=text]").first();
    await chatInput.fill("Add CALL: (555) BREW-NOW in large white text under the title");
    await chatInput.press("Enter");

    // Check ONLY the iframe, not the main page
    log("Waiting for phone in IFRAME ONLY...");
    let found = false;
    for (let i = 0; i < 60; i++) {
        await page.waitForTimeout(3000);
        
        try {
            // Use frameLocator to target only the iframe
            const iframe = page.frameLocator("iframe").first();
            const bodyText = await iframe.locator("body").innerText();
            
            if (bodyText.includes("555") || bodyText.includes("BREW-NOW")) {
                log("PHONE IN IFRAME at " + (i * 3) + "s!");
                found = true;
                break;
            }
        } catch (e) {
            // iframe might not be ready
        }
        
        if (i % 10 === 0) log("Checking... " + (i * 3) + "s");
    }

    if (!found) {
        log("Phone NOT in iframe after 180s");
    }

    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "IFRAME-02-AFTER.png"), fullPage: true });
    log("AFTER - Phone in iframe: " + found);

    await browser.close();
    log("=== DONE ===");
}

run().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
