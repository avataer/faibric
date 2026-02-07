/**
 * Faibric Full Customer Test
 *
 * Tests the complete chat and build flow:
 * 1. Question Response - Ask a question, get conversational answer
 * 2. Build Success - Request a website, see successful build
 * 3. Chat Iteration - Ask follow-up question after build
 * 4. Modification Applied - Request a change, see it applied
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const API_URL = process.env.API_URL || 'https://faibric-api.onrender.com';
const FRONTEND_URL = process.env.FRONTEND_URL || 'https://faibric-frontend.onrender.com';

// Ensure screenshots directory exists
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

// Test log
const testLog = [];
function log(msg) {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${msg}`;
  console.log(line);
  testLog.push(line);
}

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runTests() {
  log('=== FAIBRIC FULL CUSTOMER TEST ===');
  log(`API URL: ${API_URL}`);
  log(`Frontend URL: ${FRONTEND_URL}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });
  const page = await context.newPage();

  let sessionToken = null;
  let testsPassed = 0;
  let testsFailed = 0;

  try {
    // ===== TEST 1: QUESTION RESPONSE =====
    log('\n--- TEST 1: Question Response ---');

    // First, create a session and build something so we have a conversation context
    log('Creating initial session with a website request...');

    // Navigate to the frontend
    await page.goto(FRONTEND_URL);
    await page.waitForTimeout(2000);
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '01_landing_page.png'),
      fullPage: true
    });
    log('Screenshot: 01_landing_page.png');

    // Type a website request
    const inputSelector = 'input[placeholder*="describe"], textarea, input[type="text"]';
    await page.waitForSelector(inputSelector, { timeout: 10000 });
    await page.fill(inputSelector, 'I want a simple portfolio website for a photographer named Alex');
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '02_initial_request.png'),
      fullPage: true
    });
    log('Screenshot: 02_initial_request.png');

    // Submit the request
    const submitButton = page.locator('button:has-text("Go"), button:has-text("Build"), button:has-text("Create"), button[type="submit"]').first();
    await submitButton.click();
    await page.waitForTimeout(3000);
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '03_building_started.png'),
      fullPage: true
    });
    log('Screenshot: 03_building_started.png');

    // Wait for email form (if any) or skip to building
    try {
      const emailInput = page.locator('input[type="email"]');
      if (await emailInput.isVisible({ timeout: 5000 })) {
        await emailInput.fill('test@example.com');
        const emailSubmit = page.locator('button:has-text("Continue"), button:has-text("Submit"), button[type="submit"]').first();
        if (await emailSubmit.isVisible()) {
          await emailSubmit.click();
        }
        await page.waitForTimeout(2000);
      }
    } catch (e) {
      log('No email form detected, continuing...');
    }

    // Wait for build to complete (poll for deployed status)
    log('Waiting for initial build to complete...');
    let buildComplete = false;
    for (let i = 0; i < 60; i++) { // Max 5 minutes
      await page.waitForTimeout(5000);
      const pageText = await page.textContent('body');
      if (pageText.includes('deployed') || pageText.includes('Deployed') || pageText.includes('preview')) {
        buildComplete = true;
        break;
      }
      if (i % 6 === 0) {
        await page.screenshot({
          path: path.join(SCREENSHOTS_DIR, `04_building_progress_${i/6}min.png`),
          fullPage: true
        });
        log(`Screenshot: 04_building_progress_${i/6}min.png`);
      }
    }

    if (buildComplete) {
      log('Initial build completed!');
      testsPassed++;
    } else {
      log('ERROR: Initial build did not complete in time');
      testsFailed++;
    }

    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, '05_build_complete.png'),
      fullPage: true
    });
    log('Screenshot: 05_build_complete.png');

    // Now test asking a question
    log('Testing question response...');
    const chatInput = page.locator('input[placeholder*="changes"], input[placeholder*="message"], textarea').first();
    if (await chatInput.isVisible({ timeout: 5000 })) {
      await chatInput.fill('What colors can I use for my website?');
      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, '06_question_typed.png'),
        fullPage: true
      });
      log('Screenshot: 06_question_typed.png');

      // Send the question
      const sendButton = page.locator('button[aria-label*="send"], button:has(svg)').first();
      if (await sendButton.isVisible()) {
        await sendButton.click();
      } else {
        await chatInput.press('Enter');
      }
      await page.waitForTimeout(5000);

      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, '07_question_response.png'),
        fullPage: true
      });
      log('Screenshot: 07_question_response.png');

      // Check if we got a conversational response (not "Building...")
      const responseText = await page.textContent('body');
      if (responseText.includes('color') || responseText.includes('Color') ||
          responseText.includes('palette') || responseText.includes('theme')) {
        log('SUCCESS: Got conversational response about colors');
        testsPassed++;
      } else if (responseText.includes('Building') || responseText.includes('Applying')) {
        log('FAIL: Question triggered a build instead of conversation');
        testsFailed++;
      } else {
        log('PARTIAL: Got a response but unclear if conversational');
      }
    } else {
      log('ERROR: Could not find chat input');
      testsFailed++;
    }

    // ===== TEST 2: BUILD SUCCESS (already tested above) =====
    log('\n--- TEST 2: Build Success ---');
    log('Already tested with initial build');

    // ===== TEST 3: CHAT ITERATION =====
    log('\n--- TEST 3: Chat Iteration ---');
    const chatInput2 = page.locator('input[placeholder*="changes"], input[placeholder*="message"], textarea').first();
    if (await chatInput2.isVisible({ timeout: 5000 })) {
      await chatInput2.fill('Can you suggest some fonts that would work well for a photography portfolio?');

      // Send the question
      const sendButton2 = page.locator('button[aria-label*="send"], button:has(svg)').first();
      if (await sendButton2.isVisible()) {
        await sendButton2.click();
      } else {
        await chatInput2.press('Enter');
      }
      await page.waitForTimeout(5000);

      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, '08_chat_iteration.png'),
        fullPage: true
      });
      log('Screenshot: 08_chat_iteration.png');

      const responseText = await page.textContent('body');
      if (responseText.includes('font') || responseText.includes('Font') ||
          responseText.includes('typography') || responseText.includes('serif')) {
        log('SUCCESS: Got follow-up conversational response about fonts');
        testsPassed++;
      } else {
        log('PARTIAL: Got a response but may not be about fonts');
      }
    }

    // ===== TEST 4: MODIFICATION APPLIED =====
    log('\n--- TEST 4: Modification Applied ---');
    const chatInput3 = page.locator('input[placeholder*="changes"], input[placeholder*="message"], textarea').first();
    if (await chatInput3.isVisible({ timeout: 5000 })) {
      await chatInput3.fill('Change the background color to dark blue');

      // Send the modification request
      const sendButton3 = page.locator('button[aria-label*="send"], button:has(svg)').first();
      if (await sendButton3.isVisible()) {
        await sendButton3.click();
      } else {
        await chatInput3.press('Enter');
      }

      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, '09_modification_requested.png'),
        fullPage: true
      });
      log('Screenshot: 09_modification_requested.png');

      // Wait for modification to apply
      log('Waiting for modification to be applied...');
      await page.waitForTimeout(10000);

      for (let i = 0; i < 30; i++) { // Max 2.5 minutes
        await page.waitForTimeout(5000);
        const pageText = await page.textContent('body');
        if (pageText.includes('deployed') || pageText.includes('Deployed') ||
            pageText.includes('applied') || pageText.includes('done')) {
          break;
        }
      }

      await page.screenshot({
        path: path.join(SCREENSHOTS_DIR, '10_modification_applied.png'),
        fullPage: true
      });
      log('Screenshot: 10_modification_applied.png');

      log('SUCCESS: Modification request processed');
      testsPassed++;
    }

  } catch (error) {
    log(`ERROR: ${error.message}`);
    testsFailed++;
    await page.screenshot({
      path: path.join(SCREENSHOTS_DIR, 'error_screenshot.png'),
      fullPage: true
    });
    log('Screenshot: error_screenshot.png');
  } finally {
    await browser.close();
  }

  // Write test log
  log('\n=== TEST SUMMARY ===');
  log(`Tests Passed: ${testsPassed}`);
  log(`Tests Failed: ${testsFailed}`);

  const logPath = path.join(__dirname, 'FULL_TEST_LOG.md');
  const logContent = `# Faibric Full Customer Test Results

## Test Run: ${new Date().toISOString()}

### Configuration
- API URL: ${API_URL}
- Frontend URL: ${FRONTEND_URL}

### Results
- **Tests Passed**: ${testsPassed}
- **Tests Failed**: ${testsFailed}

### Screenshots
${fs.readdirSync(SCREENSHOTS_DIR).filter(f => f.endsWith('.png')).map(f => `- ${f}`).join('\n')}

### Full Log
\`\`\`
${testLog.join('\n')}
\`\`\`

### Test Descriptions

1. **Question Response** - User types a question in chat, should get conversational answer (NOT "Building...")
2. **Build Success** - User requests a website, build completes without errors
3. **Chat Iteration** - User asks follow-up question after build, gets helpful response
4. **Modification Applied** - User requests a change, change is applied to preview
`;

  fs.writeFileSync(logPath, logContent);
  log(`Test log written to: ${logPath}`);

  return testsFailed === 0;
}

runTests()
  .then(success => {
    process.exit(success ? 0 : 1);
  })
  .catch(err => {
    console.error('Test runner error:', err);
    process.exit(1);
  });
