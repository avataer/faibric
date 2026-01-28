const { chromium } = require('playwright');
const fs = require('fs');

const ARTIFACTS_DIR = '/Users/avataer/Code/Faibric/test-artifacts';

const log = (msg) => {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${msg}`;
  console.log(line);
  fs.appendFileSync(`${ARTIFACTS_DIR}/playwright_test.log`, line + '\n');
};

async function runTests() {
  log('=== FAIBRIC FEATURE TESTS ===');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  try {
    // TEST 1: Landing page loads with template buttons
    log('TEST 1: Landing page with templates');
    await page.goto('http://localhost:5173/?clear', { waitUntil: 'networkidle', timeout: 30000 });
    await page.screenshot({ path: `${ARTIFACTS_DIR}/test_01_landing.png` });

    // Check for template buttons
    const templateButtons = await page.locator('button:has-text("Restaurant")').count();
    log(`Template buttons found: ${templateButtons > 0 ? 'YES' : 'NO'}`);

    if (templateButtons > 0) {
      // Click a template button
      await page.click('button:has-text("Restaurant")');
      await page.screenshot({ path: `${ARTIFACTS_DIR}/test_02_template_clicked.png` });

      const textareaValue = await page.inputValue('textarea');
      log(`Template filled textarea: ${textareaValue.includes('restaurant') ? 'YES' : 'NO'}`);
    }

    // TEST 2: Start a build
    log('TEST 2: Starting build');
    await page.fill('textarea', 'Simple landing page with hero section and contact form');
    await page.click('button:has-text("Start Building")');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${ARTIFACTS_DIR}/test_03_building.png` });

    // Wait for deployment (max 2 min)
    log('Waiting for deployment...');
    let deployed = false;
    for (let i = 0; i < 24; i++) {
      await page.waitForTimeout(5000);
      const iframe = await page.$('iframe[title="Your Deployed Website"]');
      if (iframe) {
        log(`Deployed after ${(i+1)*5}s`);
        deployed = true;
        break;
      }
      log(`Building... ${(i+1)*5}s`);
    }

    if (!deployed) {
      log('ERROR: Build timed out');
      await page.screenshot({ path: `${ARTIFACTS_DIR}/test_ERROR_timeout.png` });
      return;
    }

    await page.screenshot({ path: `${ARTIFACTS_DIR}/test_04_deployed.png` });

    // TEST 3: Click-to-Edit feature
    log('TEST 3: Click-to-Edit');

    // Find and click the edit toggle button
    const editToggle = await page.locator('button[value="edit"]').first();
    if (await editToggle.count() > 0) {
      await editToggle.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${ARTIFACTS_DIR}/test_05_edit_mode.png` });
      log('Edit mode activated');

      // Click on the preview area
      const previewArea = await page.locator('iframe[title="Your Deployed Website"]').boundingBox();
      if (previewArea) {
        await page.mouse.click(previewArea.x + previewArea.width / 2, previewArea.y + 100);
        await page.waitForTimeout(500);
        await page.screenshot({ path: `${ARTIFACTS_DIR}/test_06_edit_dialog.png` });

        // Check if dialog opened
        const dialogVisible = await page.locator('text="What would you like to change?"').count();
        log(`Edit dialog visible: ${dialogVisible > 0 ? 'YES' : 'NO'}`);

        if (dialogVisible > 0) {
          await page.fill('textarea', 'Change the heading to "Welcome to My Site"');
          await page.screenshot({ path: `${ARTIFACTS_DIR}/test_07_edit_typed.png` });
          log('Typed edit request');
        }
      }
    } else {
      log('Edit button not found');
    }

    log('=== ALL TESTS COMPLETE ===');
    log(`Screenshots saved to ${ARTIFACTS_DIR}/`);

  } catch (error) {
    log(`ERROR: ${error.message}`);
    await page.screenshot({ path: `${ARTIFACTS_DIR}/test_ERROR.png` }).catch(() => {});
  } finally {
    await browser.close();
  }
}

runTests();
