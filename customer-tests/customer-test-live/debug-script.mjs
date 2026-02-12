import { chromium } from 'playwright';

const DEPLOY_URL = process.argv[2] || 'https://app-229-a-cozy-artisan-coffe.onrender.com';

async function debug() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

  // Capture console messages
  page.on('console', msg => console.log(`CONSOLE [${msg.type()}]: ${msg.text()}`));
  page.on('pageerror', err => console.log(`PAGE ERROR: ${err.message}`));
  page.on('requestfailed', req => console.log(`REQUEST FAILED: ${req.url()} - ${req.failure()?.errorText}`));

  console.log(`Navigating to ${DEPLOY_URL}...`);

  try {
    const response = await page.goto(DEPLOY_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    console.log(`Response status: ${response.status()}`);
    console.log(`Response URL: ${response.url()}`);

    // Wait for network to settle
    await page.waitForTimeout(10000);

    // Check root element
    const rootInfo = await page.evaluate(() => {
      const root = document.getElementById('root');
      return {
        exists: !!root,
        childCount: root ? root.children.length : 0,
        innerHTMLLength: root ? root.innerHTML.length : 0,
        innerHTMLPreview: root ? root.innerHTML.substring(0, 500) : 'no root',
        scripts: Array.from(document.scripts).map(s => ({ src: s.src, type: s.type })),
        bodyHTML: document.body.innerHTML.substring(0, 500)
      };
    });

    console.log('Root info:', JSON.stringify(rootInfo, null, 2));

  } catch (err) {
    console.error(`Error: ${err.message}`);
  } finally {
    await browser.close();
  }
}

await debug();
