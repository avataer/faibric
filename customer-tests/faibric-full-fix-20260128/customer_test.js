/**
 * Faibric Full Fix Customer Test
 *
 * Tests the complete chat flow:
 * 1. Question Response - Conversational response (not building)
 * 2. Build Success - Website builds without errors
 * 3. Chat Iteration - Follow-up question gets helpful response
 * 4. Modification Applied - Change is applied and preview updates
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const PRODUCTION_URL = 'https://faibric-frontend.onrender.com';

// Ensure screenshots directory exists
if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

function log(msg) {
    const ts = new Date().toISOString();
    console.log(`[${ts}] ${msg}`);
}

async function takeScreenshot(page, name, description) {
    const filepath = path.join(SCREENSHOTS_DIR, `${name}.png`);
    await page.screenshot({ path: filepath, fullPage: true });
    log(`Screenshot saved: ${name}.png - ${description}`);
    return filepath;
}

async function waitForElement(page, selector, options = {}) {
    const { timeout = 30000, state = 'visible' } = options;
    try {
        await page.waitForSelector(selector, { state, timeout });
        return true;
    } catch {
        return false;
    }
}

async function run() {
    log('=== FAIBRIC FULL FIX CUSTOMER TEST ===');
    log(`Testing: ${PRODUCTION_URL}`);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1400, height: 900 }
    });
    const page = await context.newPage();

    const results = {
        testName: 'Faibric Full Fix 20260128',
        timestamp: new Date().toISOString(),
        tests: []
    };

    try {
        // Load the frontend
        log('Loading Faibric frontend...');
        await page.goto(PRODUCTION_URL, { waitUntil: 'networkidle', timeout: 60000 });

        // Click "Start New" if visible
        const startNew = page.locator('button:has-text("Start New")').first();
        if (await startNew.isVisible().catch(() => false)) {
            await startNew.click();
            await page.waitForTimeout(2000);
        }

        await takeScreenshot(page, '00_initial', 'Initial landing page');

        // ============================================
        // TEST 1: Build Success
        // ============================================
        log('\n=== TEST 1: Build Success ===');

        const buildRequest = 'Create an ecommerce website for TechGear electronics store with featured products, contact form, and testimonials';
        log(`Request: ${buildRequest}`);

        const textarea = page.locator('textarea').first();
        await textarea.fill(buildRequest);

        await takeScreenshot(page, '01_build_request', 'Build request entered');

        // Submit build request
        const startBuilding = page.locator('button:has-text("Start Building")').first();
        if (await startBuilding.isVisible().catch(() => false)) {
            await startBuilding.click();
        } else {
            await page.keyboard.press('Enter');
        }

        log('Build started...');

        // Wait for deployment (up to 5 minutes)
        let deployed = false;
        let deploymentUrl = null;
        const startTime = Date.now();
        const maxWait = 300000; // 5 minutes

        while (!deployed && Date.now() - startTime < maxWait) {
            // Check for deployment status
            const deployedBtn = page.locator('button:has-text("Deployed")').first();
            const bodyText = await page.textContent('body').catch(() => '');

            if (await deployedBtn.isVisible().catch(() => false)) {
                deployed = true;
                log('Deployment complete!');
            } else if (bodyText.includes('vercel.app')) {
                const urlMatch = bodyText.match(/https:\/\/[^\s]+\.vercel\.app/);
                if (urlMatch) {
                    deployed = true;
                    deploymentUrl = urlMatch[0];
                    log(`Deployed to: ${deploymentUrl}`);
                }
            } else {
                await page.waitForTimeout(5000);
                const elapsed = Math.round((Date.now() - startTime) / 1000);
                log(`Building... ${elapsed}s`);
            }
        }

        await page.waitForTimeout(3000);
        await takeScreenshot(page, '02_build_complete', 'Build completed with preview');

        // Check for errors in the page
        const pageContent = await page.textContent('body').catch(() => '');
        const hasSyntaxError = pageContent.includes('SyntaxError') || pageContent.includes('{{@');
        const hasPreview = pageContent.includes('vercel.app') || await page.locator('iframe').first().isVisible().catch(() => false);

        results.tests.push({
            name: 'Build Success',
            passed: deployed && !hasSyntaxError && hasPreview,
            details: {
                deployed,
                deploymentUrl,
                hasSyntaxError,
                hasPreview,
                buildTime: Math.round((Date.now() - startTime) / 1000) + 's'
            }
        });

        if (!deployed) {
            log('ERROR: Build did not complete - continuing with other tests');
        }

        // ============================================
        // TEST 2: Question Response (Conversational)
        // ============================================
        log('\n=== TEST 2: Question Response ===');

        const question = 'What colors can I use for this website?';
        log(`Asking question: ${question}`);

        // Find the chat input - MUI TextField uses input element
        // The placeholder text is "Describe changes or request a new website..."
        let chatInput = page.locator('input[type="text"]').last();
        if (!await chatInput.isVisible({ timeout: 5000 }).catch(() => false)) {
            chatInput = page.locator('textarea').first();
        }
        await chatInput.waitFor({ state: 'visible', timeout: 10000 });
        await chatInput.fill(question);

        await takeScreenshot(page, '03_question_asked', 'Question entered in chat');

        // Send the question
        const sendBtn = page.locator('button').filter({ has: page.locator('svg') }).first();
        if (await sendBtn.isVisible().catch(() => false)) {
            await sendBtn.click();
        } else {
            await page.keyboard.press('Enter');
        }

        // Wait for response
        await page.waitForTimeout(5000);

        // Check for conversational response (not "Building..." or "Applying changes...")
        const responseText = await page.textContent('body').catch(() => '');
        const isConversational = !responseText.includes('Building...') &&
                                  !responseText.includes('Applying changes') &&
                                  !responseText.includes('Starting fresh');

        // Check if preview is still visible (not loading/error)
        const previewStillVisible = await page.locator('iframe').first().isVisible().catch(() => false);

        await takeScreenshot(page, '04_question_response', 'Conversational response to question');

        results.tests.push({
            name: 'Question Response',
            passed: isConversational,
            details: {
                isConversational,
                previewStillVisible,
                noRebuildTriggered: !responseText.includes('Building')
            }
        });

        // ============================================
        // TEST 3: Chat Iteration (Follow-up question)
        // ============================================
        log('\n=== TEST 3: Chat Iteration ===');

        const followUp = 'Can you explain how the navigation works?';
        log(`Follow-up question: ${followUp}`);

        await chatInput.fill(followUp);

        // Send follow-up
        if (await sendBtn.isVisible().catch(() => false)) {
            await sendBtn.click();
        } else {
            await page.keyboard.press('Enter');
        }

        await page.waitForTimeout(5000);

        const followUpResponse = await page.textContent('body').catch(() => '');
        const gotHelpfulResponse = !followUpResponse.includes('Building...') &&
                                    !followUpResponse.includes('Applying');

        await takeScreenshot(page, '05_chat_iteration', 'Follow-up question response');

        results.tests.push({
            name: 'Chat Iteration',
            passed: gotHelpfulResponse,
            details: {
                gotHelpfulResponse,
                noRebuildTriggered: !followUpResponse.includes('Building')
            }
        });

        // ============================================
        // TEST 4: Modification Applied
        // ============================================
        log('\n=== TEST 4: Modification Applied ===');

        const modification = 'Make the header background dark blue';
        log(`Modification request: ${modification}`);

        await chatInput.fill(modification);

        await takeScreenshot(page, '06_modification_request', 'Modification request entered');

        // Send modification
        if (await sendBtn.isVisible().catch(() => false)) {
            await sendBtn.click();
        } else {
            await page.keyboard.press('Enter');
        }

        // Wait for modification to be applied
        log('Waiting for modification to apply...');
        const modStart = Date.now();
        const modMaxWait = 180000; // 3 minutes
        let modificationApplied = false;

        while (!modificationApplied && Date.now() - modStart < modMaxWait) {
            await page.waitForTimeout(5000);
            const text = await page.textContent('body').catch(() => '');

            // Check if "Applying changes" message appeared (means it's a command, not question)
            if (text.includes('Applying') || text.includes('Got it')) {
                log('Modification being applied...');
            }

            // Check for new deployment
            const deployedAgain = await page.locator('button:has-text("Deployed")').first().isVisible().catch(() => false);
            if (deployedAgain) {
                modificationApplied = true;
                log('Modification deployed!');
            }

            const elapsed = Math.round((Date.now() - modStart) / 1000);
            if (elapsed % 15 === 0) {
                log(`Waiting... ${elapsed}s`);
            }
        }

        await page.waitForTimeout(3000);
        await takeScreenshot(page, '07_modification_applied', 'Modification applied and preview updated');

        results.tests.push({
            name: 'Modification Applied',
            passed: modificationApplied,
            details: {
                modificationApplied,
                modificationTime: Math.round((Date.now() - modStart) / 1000) + 's'
            }
        });

        // ============================================
        // Final Summary
        // ============================================
        log('\n=== TEST RESULTS ===');

        let allPassed = true;
        for (const test of results.tests) {
            const status = test.passed ? 'PASS' : 'FAIL';
            log(`${status}: ${test.name}`);
            if (!test.passed) allPassed = false;
        }

        results.overallPassed = allPassed;
        results.summary = allPassed ? 'All tests passed!' : 'Some tests failed';

        // Save results
        fs.writeFileSync(
            path.join(SCREENSHOTS_DIR, 'test_results.json'),
            JSON.stringify(results, null, 2)
        );

        log(`\nOverall: ${allPassed ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED'}`);

        return results;

    } catch (e) {
        log(`ERROR: ${e.message}`);
        await takeScreenshot(page, 'error', 'Error during test');
        throw e;
    } finally {
        await browser.close();
    }
}

run()
    .then(results => {
        console.log(JSON.stringify(results, null, 2));
        process.exit(results.overallPassed ? 0 : 1);
    })
    .catch(e => {
        console.error(e);
        process.exit(1);
    });
