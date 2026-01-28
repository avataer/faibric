const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const SCREENSHOTS_DIR = "/Users/avataer/Code/Faibric/customer-tests/coffee-shop-menu/screenshots";

async function run() {
    const browser = await chromium.launch({ headless: true });
    
    // Capture the BEFORE site (initial deployment - no phone)
    const page1 = await browser.newPage();
    page1.setViewportSize({ width: 1280, height: 900 });
    await page1.goto("https://appu0s0iwhi14-kaozw3t6b-antons-projects-f1d70cf2.vercel.app", { waitUntil: "networkidle" });
    await page1.waitForTimeout(2000);
    await page1.screenshot({ path: path.join(SCREENSHOTS_DIR, "PROOF-01-BEFORE-no-phone.png"), fullPage: true });
    console.log("Captured BEFORE (no phone)");
    await page1.close();

    // Capture the AFTER site (after modification - WITH phone)
    const page2 = await browser.newPage();
    page2.setViewportSize({ width: 1280, height: 900 });
    await page2.goto("https://appb03os76i6i-m5ypm4fgn-antons-projects-f1d70cf2.vercel.app", { waitUntil: "networkidle" });
    await page2.waitForTimeout(2000);
    await page2.screenshot({ path: path.join(SCREENSHOTS_DIR, "PROOF-02-AFTER-with-phone.png"), fullPage: true });
    console.log("Captured AFTER (WITH phone)");
    await page2.close();

    await browser.close();
    console.log("Done");
}

run();
