import { chromium } from 'playwright';

const URL = 'https://app-229-a-cozy-artisan-coffe.onrender.com';
const BASE = '/Users/avataer/Code/Faibric/customer-tests/customer-test-live';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  console.log('Navigating to deployed site...');
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(5000);

  // Take after screenshot
  await page.screenshot({
    path: `${BASE}/deployed-site-after-modification.png`,
    fullPage: true
  });
  console.log('After screenshot saved');

  // Extract ALL class attributes for color verification
  const classData = await page.evaluate(() => {
    const elements = document.querySelectorAll('*');
    const allClasses = [];
    elements.forEach(el => {
      const cls = el.getAttribute('class');
      if (cls) allClasses.push(...cls.split(/\s+/));
    });
    return allClasses;
  });

  // Count color classes by family
  const colorFamilies = {};
  const bgClasses = {};
  const textClasses = {};
  const gradientClasses = {};
  const borderClasses = {};

  classData.forEach(cls => {
    // Background classes
    if (cls.match(/^bg-/)) {
      bgClasses[cls] = (bgClasses[cls] || 0) + 1;
    }
    // Text color classes
    if (cls.match(/^text-[a-z]+-[0-9]+$/)) {
      textClasses[cls] = (textClasses[cls] || 0) + 1;
    }
    // Gradient classes
    if (cls.match(/^(from|to|via)-/)) {
      gradientClasses[cls] = (gradientClasses[cls] || 0) + 1;
    }
    // Border classes
    if (cls.match(/^border-[a-z]+-/)) {
      borderClasses[cls] = (borderClasses[cls] || 0) + 1;
    }
  });

  // Count by color family
  const families = { amber: 0, stone: 0, brown: 0, yellow: 0, gray: 0, blue: 0, violet: 0, purple: 0, white: 0 };
  classData.forEach(cls => {
    for (const family of Object.keys(families)) {
      if (cls.includes(family)) families[family]++;
    }
  });

  let output = `=== COLOR VERIFICATION (Playwright DOM Analysis) ===\n`;
  output += `URL: ${URL}\n`;
  output += `Timestamp: ${new Date().toISOString()}\n\n`;

  output += `--- Background classes ---\n`;
  Object.entries(bgClasses).sort((a,b) => b[1]-a[1]).forEach(([cls, count]) => {
    output += `  ${count}\t${cls}\n`;
  });

  output += `\n--- Text color classes ---\n`;
  Object.entries(textClasses).sort((a,b) => b[1]-a[1]).forEach(([cls, count]) => {
    output += `  ${count}\t${cls}\n`;
  });

  output += `\n--- Gradient classes ---\n`;
  Object.entries(gradientClasses).sort((a,b) => b[1]-a[1]).forEach(([cls, count]) => {
    output += `  ${count}\t${cls}\n`;
  });

  output += `\n--- Border classes ---\n`;
  Object.entries(borderClasses).sort((a,b) => b[1]-a[1]).forEach(([cls, count]) => {
    output += `  ${count}\t${cls}\n`;
  });

  output += `\n=== COLOR FAMILY SUMMARY ===\n`;
  for (const [family, count] of Object.entries(families)) {
    output += `${family}: ${count}\n`;
  }

  // Verification
  const warmColors = families.amber + families.stone + families.brown + families.yellow;
  const unwantedColors = families.violet + families.purple + families.gray + families.blue;

  output += `\n=== VERIFICATION ===\n`;
  output += `Total warm colors (amber+stone+brown+yellow): ${warmColors}\n`;
  output += `Total unwanted colors (violet+purple+gray+blue): ${unwantedColors}\n`;
  output += `\n`;

  if (warmColors > 0 && families.violet === 0 && families.purple === 0) {
    output += `VERDICT: PASS - Warm brown/amber colors present, NO violet/purple found\n`;
  } else if (warmColors > 0 && unwantedColors > 0) {
    output += `VERDICT: PARTIAL - Warm colors present but unwanted colors still found\n`;
  } else {
    output += `VERDICT: FAIL - Missing warm colors or unwanted colors present\n`;
  }

  // Check for tagline
  const pageContent = await page.textContent('body');
  const hasTagline = pageContent.includes('Fresh Brews, Warm Hearts');
  output += `\nTagline "Fresh Brews, Warm Hearts" visible: ${hasTagline}\n`;

  // Write the file
  const fs = await import('fs');
  fs.writeFileSync(`${BASE}/color-verification.txt`, output);
  console.log('Color verification saved');
  console.log(output);

  await browser.close();
})();
