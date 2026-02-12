import { chromium } from 'playwright';

async function run() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

  // Capture network requests to the API
  const apiRequests = [];
  page.on('request', req => {
    if (req.url().includes('faibric-api') || req.url().includes('onrender.com/api')) {
      apiRequests.push({ url: req.url(), method: req.method() });
    }
  });

  page.on('response', async resp => {
    if (resp.url().includes('faibric-api') || resp.url().includes('/api/')) {
      try {
        const body = await resp.text();
        console.log(`\nAPI Response [${resp.status()}]: ${resp.url()}`);
        // Check if response has amber
        if (body.includes('amber')) {
          console.log('  -> Contains "amber"');
        }
        if (body.includes('Fresh Brews')) {
          console.log('  -> Contains "Fresh Brews"');
        }
        if (body.includes('gray-900')) {
          console.log('  -> Contains "gray-900"');
        }
        console.log(`  -> Body length: ${body.length}`);
        // Print first 500 chars of generated code if present
        if (body.length > 100) {
          const preview = body.substring(0, 500);
          console.log(`  -> Preview: ${preview}`);
        }
      } catch (e) {
        console.log(`  -> Could not read body: ${e.message}`);
      }
    }
  });

  console.log('Navigating to deployed site...');
  await page.goto('https://app-229-a-cozy-artisan-coffe.onrender.com', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(5000);

  console.log('\n=== API Requests Made ===');
  apiRequests.forEach(r => console.log(`  ${r.method} ${r.url}`));

  await browser.close();
}

run().catch(err => { console.error(err); process.exit(1); });
