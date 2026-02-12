const { chromium } = require("playwright");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

  // Screenshot 1: Deployed site (current state)
  console.log("Navigating to deployed site...");
  await page.goto("https://app-229-a-cozy-artisan-coffe.onrender.com", { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: "/Users/avataer/Code/Faibric/customer-tests/customer-test-live/deployed-site-after-modification.png", fullPage: true });
  console.log("Deployed site screenshot taken");

  // Get rendered HTML for color verification
  const html = await page.content();
  const fs = require("fs");
  fs.writeFileSync("/Users/avataer/Code/Faibric/customer-tests/customer-test-live/rendered-html-final.txt", html);

  // Extract all classes for color verification
  const allClasses = await page.evaluate(() => {
    const elements = document.querySelectorAll("*");
    const classes = [];
    elements.forEach(el => {
      el.classList.forEach(c => { if (c.startsWith("bg-") || c.startsWith("text-") || c.startsWith("from-") || c.startsWith("to-") || c.startsWith("border-")) classes.push(c); });
    });
    return classes;
  });

  // Count color classes
  const counts = {};
  allClasses.forEach(c => { counts[c] = (counts[c] || 0) + 1; });
  const sorted = Object.entries(counts).sort((a,b) => b[1] - a[1]);

  let verification = "=== COLOR VERIFICATION (Rendered DOM) ===\n";
  verification += "URL: https://app-229-a-cozy-artisan-coffe.onrender.com\n";
  verification += "Timestamp: " + new Date().toISOString() + "\n\n";
  verification += "--- All color classes ---\n";
  sorted.forEach(([cls, count]) => { verification += "  " + count + " " + cls + "\n"; });

  const amberCount = sorted.filter(([c]) => c.includes("amber")).reduce((sum, [,c]) => sum + c, 0);
  const stoneCount = sorted.filter(([c]) => c.includes("stone")).reduce((sum, [,c]) => sum + c, 0);
  const brownCount = sorted.filter(([c]) => c.includes("brown") || c.includes("yellow-9") || c.includes("yellow-8")).reduce((sum, [,c]) => sum + c, 0);
  const grayCount = sorted.filter(([c]) => c.includes("gray")).reduce((sum, [,c]) => sum + c, 0);
  const violetCount = sorted.filter(([c]) => c.includes("violet") || c.includes("purple")).reduce((sum, [,c]) => sum + c, 0);

  verification += "\n--- Summary ---\n";
  verification += "Amber classes: " + amberCount + "\n";
  verification += "Stone classes: " + stoneCount + "\n";
  verification += "Brown/warm classes: " + brownCount + "\n";
  verification += "Gray classes: " + grayCount + "\n";
  verification += "Violet/Purple classes: " + violetCount + "\n";

  const hasWarmColors = amberCount > 0 || stoneCount > 0 || brownCount > 0;
  const hasUnwantedColors = violetCount > 0;

  verification += "\nVERDICT: " + (hasWarmColors && !hasUnwantedColors ? "PASS - Warm colors present, no violet/purple" : "NEEDS ATTENTION") + "\n";
  if (!hasWarmColors) verification += "WARNING: No warm amber/stone/brown colors found\n";
  if (hasUnwantedColors) verification += "WARNING: Violet/purple colors still present\n";

  fs.writeFileSync("/Users/avataer/Code/Faibric/customer-tests/customer-test-live/color-verification.txt", verification);
  console.log("Color verification saved");
  console.log(verification);

  // Screenshot 2: Frontend homepage
  console.log("Navigating to frontend...");
  await page.goto("https://faibric-frontend.onrender.com", { waitUntil: "networkidle", timeout: 120000 });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: "/Users/avataer/Code/Faibric/customer-tests/customer-test-live/frontend-homepage.png", fullPage: true });
  console.log("Frontend screenshot taken");

  await browser.close();
  console.log("Screenshots and color verification complete");
})();
