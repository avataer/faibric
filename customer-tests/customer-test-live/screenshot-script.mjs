import { chromium } from 'playwright';

const DEPLOY_URL = process.argv[2] || 'https://app-229-a-cozy-artisan-coffe.onrender.com';
const OUTPUT_DIR = '/Users/avataer/Code/Faibric/customer-tests/customer-test-live';

async function takeScreenshot(url, filename, label) {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

  console.log(`[${label}] Navigating to ${url}...`);

  try {
    // Navigate with extended timeout for Render cold start
    await page.goto(url, { waitUntil: 'networkidle', timeout: 120000 });

    // Wait for React to render - look for content in #root
    console.log(`[${label}] Waiting for React to render...`);
    await page.waitForFunction(() => {
      const root = document.getElementById('root');
      return root && root.children.length > 0 && root.innerHTML.length > 100;
    }, { timeout: 60000 });

    // Extra wait for CSS/images
    await page.waitForTimeout(3000);

    // Take full-page screenshot
    await page.screenshot({ path: `${OUTPUT_DIR}/${filename}`, fullPage: true });
    console.log(`[${label}] Screenshot saved to ${OUTPUT_DIR}/${filename}`);

    // Extract rendered HTML for color verification
    const html = await page.content();
    const fs = await import('fs');
    fs.writeFileSync(`${OUTPUT_DIR}/rendered-html.txt`, html);
    console.log(`[${label}] Rendered HTML saved`);

    // Extract color classes from rendered DOM
    const colorData = await page.evaluate(() => {
      const allElements = document.querySelectorAll('*');
      const classes = [];
      allElements.forEach(el => {
        el.classList.forEach(cls => {
          if (cls.match(/^(bg|text|from|to|border)-[a-z]+-[0-9]+$/)) {
            classes.push(cls);
          }
        });
      });
      return classes;
    });

    // Count occurrences
    const counts = {};
    colorData.forEach(cls => { counts[cls] = (counts[cls] || 0) + 1; });
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);

    let colorReport = '=== COLOR CLASSES FROM RENDERED DOM ===\n';
    sorted.forEach(([cls, count]) => {
      colorReport += `  ${count}\t${cls}\n`;
    });

    fs.writeFileSync(`${OUTPUT_DIR}/color-classes-rendered.txt`, colorReport);
    console.log(`[${label}] Color classes extracted`);
    console.log(colorReport);

  } catch (err) {
    console.error(`[${label}] Error: ${err.message}`);
    // Still try to take screenshot even on error
    try {
      await page.screenshot({ path: `${OUTPUT_DIR}/${filename}`, fullPage: true });
      console.log(`[${label}] Fallback screenshot saved`);
    } catch (e) {
      console.error(`[${label}] Fallback screenshot also failed: ${e.message}`);
    }
  } finally {
    await browser.close();
  }
}

await takeScreenshot(DEPLOY_URL, 'deployed-site-after-modification.png', 'AFTER');
