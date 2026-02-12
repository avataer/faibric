import { chromium } from 'playwright';
import fs from 'fs';

const DEPLOY_URL = 'https://app-229-a-cozy-artisan-coffe.onrender.com';
const OUTPUT_DIR = '/Users/avataer/Code/Faibric/customer-tests/customer-test-live';

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  // Capture console errors
  page.on('pageerror', err => console.log(`PAGE ERROR: ${err.message}`));

  console.log(`Navigating to ${DEPLOY_URL}...`);
  await page.goto(DEPLOY_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });

  // Wait for React to mount
  await page.waitForFunction(() => {
    const root = document.getElementById('root');
    return root && root.innerHTML.length > 100;
  }, { timeout: 30000 });

  // Wait for CSS to load
  await page.waitForTimeout(5000);

  // Take after screenshot
  await page.screenshot({ path: `${OUTPUT_DIR}/deployed-site-after-modification.png`, fullPage: true });
  console.log('After screenshot saved');

  // Save rendered HTML
  const html = await page.content();
  fs.writeFileSync(`${OUTPUT_DIR}/rendered-html.txt`, html);

  // Extract ALL class names that are color-related
  const colorData = await page.evaluate(() => {
    const allElements = document.querySelectorAll('*');
    const classes = [];
    allElements.forEach(el => {
      el.classList.forEach(cls => {
        if (cls.match(/^(bg|text|from|to|border|ring|shadow)-/)) {
          classes.push(cls);
        }
      });
    });
    return classes;
  });

  // Count and sort
  const counts = {};
  colorData.forEach(cls => { counts[cls] = (counts[cls] || 0) + 1; });
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);

  let report = '=== COLOR/STYLING CLASSES FROM RENDERED DOM ===\n';
  report += `URL: ${DEPLOY_URL}\n`;
  report += `Timestamp: ${new Date().toISOString()}\n\n`;

  // Separate bg classes
  report += '--- Background classes ---\n';
  sorted.filter(([c]) => c.startsWith('bg-')).forEach(([cls, count]) => {
    report += `  ${count}\t${cls}\n`;
  });

  report += '\n--- Text color classes ---\n';
  sorted.filter(([c]) => c.startsWith('text-')).forEach(([cls, count]) => {
    report += `  ${count}\t${cls}\n`;
  });

  report += '\n--- Gradient classes ---\n';
  sorted.filter(([c]) => c.startsWith('from-') || c.startsWith('to-')).forEach(([cls, count]) => {
    report += `  ${count}\t${cls}\n`;
  });

  report += '\n--- Border classes ---\n';
  sorted.filter(([c]) => c.startsWith('border-')).forEach(([cls, count]) => {
    report += `  ${count}\t${cls}\n`;
  });

  // Color verification
  const bgClasses = sorted.filter(([c]) => c.startsWith('bg-'));
  const grayBg = bgClasses.filter(([c]) => c.includes('-gray-'));
  const blueBg = bgClasses.filter(([c]) => c.includes('-blue-'));
  const amberBg = bgClasses.filter(([c]) => c.includes('-amber-'));
  const stoneBg = bgClasses.filter(([c]) => c.includes('-stone-'));
  const yellowBg = bgClasses.filter(([c]) => c.includes('-yellow-'));

  report += '\n=== COLOR VERIFICATION ===\n';
  report += `Gray bg classes: ${grayBg.map(([c, n]) => `${c}(${n})`).join(', ') || 'NONE'}\n`;
  report += `Blue bg classes: ${blueBg.map(([c, n]) => `${c}(${n})`).join(', ') || 'NONE'}\n`;
  report += `Amber bg classes: ${amberBg.map(([c, n]) => `${c}(${n})`).join(', ') || 'NONE'}\n`;
  report += `Stone bg classes: ${stoneBg.map(([c, n]) => `${c}(${n})`).join(', ') || 'NONE'}\n`;
  report += `Yellow bg classes: ${yellowBg.map(([c, n]) => `${c}(${n})`).join(', ') || 'NONE'}\n`;

  const grayCount = grayBg.reduce((s, [, n]) => s + n, 0);
  const blueCount = blueBg.reduce((s, [, n]) => s + n, 0);
  const warmCount = amberBg.reduce((s, [, n]) => s + n, 0) + stoneBg.reduce((s, [, n]) => s + n, 0) + yellowBg.reduce((s, [, n]) => s + n, 0);

  report += `\nTotal gray bg: ${grayCount}\n`;
  report += `Total blue bg: ${blueCount}\n`;
  report += `Total warm (amber+stone+yellow) bg: ${warmCount}\n`;

  if (grayCount === 0 && blueCount === 0) {
    report += '\nVERDICT: PASS - No unwanted gray/blue backgrounds\n';
  } else {
    report += `\nVERDICT: WARNING - Found gray(${grayCount}) blue(${blueCount}) backgrounds\n`;
  }

  if (warmCount > 0) {
    report += 'VERDICT: PASS - Warm colors present\n';
  } else {
    report += 'VERDICT: WARNING - No warm amber/stone/yellow backgrounds found\n';
  }

  fs.writeFileSync(`${OUTPUT_DIR}/color-verification.txt`, report);
  console.log(report);

  await browser.close();
}

run().catch(err => { console.error(err); process.exit(1); });
