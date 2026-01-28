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
    }
    return false;
}

async function run() {
    log("=== FINAL CHECK TEST ===");

    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1600, height: 1000 });

    await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

    log("Building...");
    const textarea = await page.locator("textarea").first();
    await textarea.fill("Bean & Brew. Just hero. Brown/cream. Minimal.");

    await page.locator("button:has-text(\"Start Building\")").first().click();
    log("Waiting for build...");
    await waitForBuild(page, 180000);
    await page.waitForTimeout(5000);
    
    // Get initial URL from iframe
    let initialUrl = "";
    try {
        const iframeSrc = await page.locator("iframe").first().getAttribute("src");
        initialUrl = iframeSrc || "";
        log("Initial iframe URL: " + initialUrl);
    } catch {}

    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "FINALCHECK-01-BEFORE.png"), fullPage: true });

    log("Sending amendment...");
    const chatInput = await page.locator("input[type=text]").first();
    await chatInput.fill("Add CALL: (555) NOW in hero");
    await chatInput.press("Enter");

    // Monitor iframe URL changes
    log("Monitoring for URL change...");
    for (let i = 0; i < 40; i++) {
        await page.waitForTimeout(3000);
        
        try {
            const currentUrl = await page.locator("iframe").first().getAttribute("src");
            if (currentUrl && currentUrl !== initialUrl) {
                log("IFRAME URL CHANGED at " + (i * 3) + "s!");
                log("New URL: " + currentUrl);
                
                // Check if new URL has phone
                const response = await page.request.get(currentUrl);
                const html = await response.text();
                const hasPhone = html.includes("555");
                log("New URL has phone: " + hasPhone);
                
                break;
            }
        } catch {}
        
        if (i % 10 === 0) log("Waiting... " + (i * 3) + "s");
    }

    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, "FINALCHECK-02-AFTER.png"), fullPage: true });
    log("DONE");

    await browser.close();
}

run().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
