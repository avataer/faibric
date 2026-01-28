const { chromium } = require("playwright");
const ARTIFACT_DIR = "/Users/avataer/Code/Faibric/test-artifacts";

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  console.log("=== PRODUCTION TEST ===");
  console.log("Testing: https://faibric-frontend.onrender.com");

  await page.goto("https://faibric-frontend.onrender.com");
  await page.waitForTimeout(3000);
  await page.screenshot({ path: ARTIFACT_DIR + "/prod_01_landing.png" });
  console.log("Screenshot: prod_01_landing.png");

  // Look for create/build button
  const createBtn = page.locator("text=Create").first();
  const buildBtn = page.locator("text=Build").first();
  const startBtn = page.locator("text=Start").first();
  
  if (await createBtn.isVisible()) {
    await createBtn.click();
    console.log("Clicked Create");
  } else if (await startBtn.isVisible()) {
    await startBtn.click();
    console.log("Clicked Start");
  }
  
  await page.waitForTimeout(2000);
  await page.screenshot({ path: ARTIFACT_DIR + "/prod_02_after_click.png" });
  console.log("Screenshot: prod_02_after_click.png");

  // Try to find textarea and enter request
  const textarea = page.locator("textarea").first();
  if (await textarea.isVisible()) {
    await textarea.fill("Create a simple landing page for a coffee shop");
    console.log("Entered request");
    await page.screenshot({ path: ARTIFACT_DIR + "/prod_03_request.png" });
    
    // Click build
    const buildButton = page.locator("button:has-text(\"Build\")").first();
    if (await buildButton.isVisible()) {
      await buildButton.click();
      console.log("Clicked Build");
    }
  }

  // Wait and see what happens
  console.log("Waiting 60s for build...");
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(2000);
    if (i % 5 === 0) {
      await page.screenshot({ path: ARTIFACT_DIR + "/prod_04_waiting_" + i + ".png" });
      console.log("Screenshot at " + (i*2) + "s");
    }
  }

  await page.screenshot({ path: ARTIFACT_DIR + "/prod_05_final.png" });
  console.log("Final screenshot: prod_05_final.png");

  await browser.close();
})();
