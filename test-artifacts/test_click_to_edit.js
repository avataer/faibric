const { chromium } = require('playwright');
const fs = require('fs');

const log = (msg) => {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${msg}`;
  console.log(line);
  fs.appendFileSync('/Users/avataer/Code/Faibric/test-artifacts/click_to_edit_test.log', line + '\n');
};

async function testClickToEdit() {
  log('=== CLICK-TO-EDIT FEATURE TEST ===');

  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage();
    await page.setViewportSize({ width: 1400, height: 900 });

    // Load local frontend
    log('Loading local frontend...');
    await page.goto('http://localhost:5173/?clear', { waitUntil: 'networkidle', timeout: 30000 });
    await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/01_landing_page.png' });
    log('Screenshot: 01_landing_page.png');

    // Enter a build request
    log('Entering build request...');
    await page.waitForSelector('textarea', { timeout: 10000 });
    await page.fill('textarea', 'Create a simple landing page for a coffee shop called Bean Brew with a welcome message and phone number');
    await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/02_request_entered.png' });
    log('Screenshot: 02_request_entered.png');

    // Click Start Building
    log('Clicking Start Building...');
    await page.click('button:has-text("Start Building")');

    log('Waiting for build to start...');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/03_building_started.png' });
    log('Screenshot: 03_building_started.png');

    // Wait for deployment (with timeout)
    log('Waiting for deployment (max 3 minutes)...');
    let deployed = false;
    for (let i = 0; i < 36; i++) {  // 36 * 5s = 180s = 3 minutes
      await page.waitForTimeout(5000);

      // Check for iframe with deployment URL
      const iframe = await page.$('iframe[title="Your Deployed Website"]');
      if (iframe) {
        log(`Deployment iframe detected after ${(i+1)*5} seconds`);
        deployed = true;
        break;
      }

      log(`Still building... ${(i+1)*5}s`);
    }

    if (!deployed) {
      log('ERROR: Deployment timed out');
      await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/ERROR_timeout.png' });
      return;
    }

    await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/04_deployed.png' });
    log('Screenshot: 04_deployed.png');

    // Find and click the edit mode toggle button
    log('Looking for edit mode button...');
    await page.waitForTimeout(2000);

    // Click on the toggle button with TouchAppIcon
    const editButton = await page.locator('button').filter({ has: page.locator('svg[data-testid="TouchAppIcon"]') }).first();
    if (await editButton.count() > 0) {
      await editButton.click();
      log('Clicked edit mode button');
    } else {
      log('Edit button not found by icon, trying value selector');
      // Try alternate selector
      const toggleBtn = await page.locator('[value="edit"]').first();
      if (await toggleBtn.count() > 0) {
        await toggleBtn.click();
        log('Clicked toggle button');
      }
    }

    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/05_edit_mode_enabled.png' });
    log('Screenshot: 05_edit_mode_enabled.png - EDIT MODE SHOULD BE VISIBLE');

    // Click on the preview overlay to open edit dialog
    log('Clicking on preview overlay...');
    // The overlay should be on top when edit mode is active
    await page.click('text="Click anywhere on the preview to edit that area"', { timeout: 5000 }).catch(() => {
      log('Could not click text, trying coordinates');
    });

    // Alternative: click by coordinates in the preview area
    const previewBox = await page.locator('.MuiBox-root').filter({ has: page.locator('iframe') }).first().boundingBox();
    if (previewBox) {
      await page.mouse.click(previewBox.x + previewBox.width / 2, previewBox.y + previewBox.height / 2);
      log('Clicked on preview coordinates');
    }

    await page.waitForTimeout(1000);
    await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/06_edit_dialog.png' });
    log('Screenshot: 06_edit_dialog.png - EDIT DIALOG SHOULD BE VISIBLE');

    // Check if dialog appeared
    const dialog = await page.locator('text="What would you like to change?"').count();
    if (dialog > 0) {
      log('SUCCESS: Edit dialog is visible!');

      // Type something in the dialog
      await page.fill('textarea', 'Change the welcome message to "Welcome to Bean Brew Coffee!"');
      await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/07_edit_typed.png' });
      log('Screenshot: 07_edit_typed.png');
    } else {
      log('WARNING: Edit dialog not visible');
    }

    log('=== TEST COMPLETE ===');
    log('Check screenshots in /Users/avataer/Code/Faibric/test-artifacts/');

  } catch (error) {
    log(`ERROR: ${error.message}`);
    await page.screenshot({ path: '/Users/avataer/Code/Faibric/test-artifacts/ERROR_final.png' }).catch(() => {});
  } finally {
    await browser.close();
  }
}

testClickToEdit();
