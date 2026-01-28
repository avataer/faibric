const { chromium } = require("playwright");
const fs = require("fs");

async function run() {
    console.log("Starting quick test...");
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    page.setViewportSize({ width: 1400, height: 900 });

    await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });

    // Quick build
    const textarea = await page.locator("textarea").first();
    await textarea.fill("Simple landing page for Test Coffee Shop. Brown colors. Just a hero section.");
    await page.locator("button:has-text(\"Start Building\")").first().click();
    
    console.log("Building...");
    for (let i = 0; i < 60; i++) {
        await page.waitForTimeout(3000);
        const deployed = await page.locator("button:has-text(\"Deployed\")").first();
        if (await deployed.isVisible().catch(() => false)) {
            console.log("Build complete at " + (i * 3) + "s");
            break;
        }
    }
    
    await page.waitForTimeout(3000);
    
    // Send amendment
    console.log("Sending amendment...");
    const chatInput = await page.locator("input[type=text]").first();
    await chatInput.fill("Add PHONE: 555-1234 in big text");
    await chatInput.press("Enter");
    
    console.log("Waiting 30s for Celery...");
    await page.waitForTimeout(30000);
    
    await page.screenshot({ path: "/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu/screenshots/quick-result.png", fullPage: true });
    console.log("Screenshot saved");
    
    await browser.close();
    console.log("Done");
}

run().catch(e => { console.error(e); process.exit(1); });
