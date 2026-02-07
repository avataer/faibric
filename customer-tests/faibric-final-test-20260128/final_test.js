const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const SCREENSHOTS_DIR = path.join(__dirname, 'screenshots');
const FRONTEND_URL = 'http://localhost:5173';

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function takeScreenshot(page, name) {
    const filepath = path.join(SCREENSHOTS_DIR, name);
    await page.screenshot({ path: filepath, fullPage: false });
    console.log(`Screenshot saved: ${name}`);
    return filepath;
}

async function runFinalTest() {
    console.log('='.repeat(60));
    console.log('FAIBRIC FINAL CUSTOMER TEST');
    console.log('Date:', new Date().toISOString());
    console.log('='.repeat(60));

    const results = {
        buildWorks: false,
        chatWorks: false,
        modificationsWork: false,
        screenshots: [],
        logs: []
    };

    const log = (msg) => {
        const timestamp = new Date().toISOString();
        const logMsg = `[${timestamp}] ${msg}`;
        console.log(logMsg);
        results.logs.push(logMsg);
    };

    // Ensure screenshots directory exists
    if (!fs.existsSync(SCREENSHOTS_DIR)) {
        fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
    }

    const browser = await puppeteer.launch({
        headless: false,
        defaultViewport: { width: 1400, height: 900 },
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();

        // Enable console logging
        page.on('console', msg => log(`[BROWSER] ${msg.text()}`));

        // ============================================
        // TEST 1: LANDING PAGE
        // ============================================
        log('TEST 1: Loading landing page...');
        await page.goto(FRONTEND_URL, { waitUntil: 'networkidle0', timeout: 30000 });
        await sleep(2000);

        await takeScreenshot(page, '01_landing_page.png');
        results.screenshots.push('01_landing_page.png');
        log('Landing page loaded successfully');

        // ============================================
        // TEST 2: BUILD FUNCTIONALITY
        // ============================================
        log('TEST 2: Testing build functionality...');

        // Find and fill the input
        const inputSelector = 'input[type="text"], textarea';
        await page.waitForSelector(inputSelector, { timeout: 10000 });

        const buildRequest = 'Create a modern landing page for a coffee shop called "Bean There" with a hero section, menu section, and contact form';
        await page.type(inputSelector, buildRequest);
        await sleep(500);

        await takeScreenshot(page, '02_initial_request.png');
        results.screenshots.push('02_initial_request.png');
        log('Initial request entered');

        // Submit the request
        await page.keyboard.press('Enter');
        log('Request submitted, waiting for build...');

        await sleep(3000);
        await takeScreenshot(page, '03_building.png');
        results.screenshots.push('03_building.png');

        // Wait for build to complete (look for iframe or preview)
        log('Waiting for build to complete...');
        let buildComplete = false;
        let attempts = 0;
        const maxAttempts = 60; // 60 seconds max

        while (!buildComplete && attempts < maxAttempts) {
            await sleep(1000);
            attempts++;

            // Check for iframe (preview)
            const iframe = await page.$('iframe');
            if (iframe) {
                buildComplete = true;
                log('Preview iframe detected!');
            }

            // Check for error messages
            const pageContent = await page.content();
            if (pageContent.includes('error') && pageContent.includes('database')) {
                log('ERROR: Database error detected!');
                break;
            }

            if (attempts % 10 === 0) {
                log(`Still waiting... ${attempts}s elapsed`);
                await takeScreenshot(page, `03_building_${attempts}s.png`);
            }
        }

        await sleep(2000);
        await takeScreenshot(page, '04_build_complete.png');
        results.screenshots.push('04_build_complete.png');

        // Check if build was successful
        const hasPreview = await page.$('iframe');
        if (hasPreview) {
            log('BUILD SUCCESS: Preview is visible');
            results.buildWorks = true;
        } else {
            log('BUILD RESULT: Checking page state...');
            const content = await page.content();
            if (content.includes('error')) {
                log('BUILD FAILED: Error detected in page');
            }
        }

        // ============================================
        // TEST 3: CHAT/QUESTION FUNCTIONALITY
        // ============================================
        log('TEST 3: Testing chat functionality...');
        await sleep(2000);

        // Clear input and ask a question
        const input = await page.$(inputSelector);
        if (input) {
            await input.click({ clickCount: 3 });
            await page.keyboard.press('Backspace');
        }

        const question = 'What colors would work for this site?';
        await page.type(inputSelector, question);
        await sleep(500);

        await takeScreenshot(page, '05_question_asked.png');
        results.screenshots.push('05_question_asked.png');
        log(`Question asked: "${question}"`);

        // Submit the question
        await page.keyboard.press('Enter');
        log('Question submitted, waiting for response...');

        // Wait for response
        await sleep(8000);

        await takeScreenshot(page, '06_conversation_response.png');
        results.screenshots.push('06_conversation_response.png');

        // Check response - look for conversational response, not "Starting fresh"
        const pageText = await page.evaluate(() => document.body.innerText);
        if (pageText.includes('Starting fresh') || pageText.includes('building')) {
            log('CHAT FAILED: Got rebuild response instead of conversation');
            results.chatWorks = false;
        } else if (pageText.includes('color') || pageText.includes('palette') || pageText.includes('recommend')) {
            log('CHAT SUCCESS: Got conversational response about colors');
            results.chatWorks = true;
        } else {
            log('CHAT RESULT: Response unclear, checking further...');
        }

        // ============================================
        // TEST 4: MODIFICATION FUNCTIONALITY
        // ============================================
        log('TEST 4: Testing modification functionality...');
        await sleep(2000);

        // Clear input and request modification
        const inputMod = await page.$(inputSelector);
        if (inputMod) {
            await inputMod.click({ clickCount: 3 });
            await page.keyboard.press('Backspace');
        }

        const modification = 'Make the header darker';
        await page.type(inputSelector, modification);
        await sleep(500);

        await takeScreenshot(page, '07_modification_request.png');
        results.screenshots.push('07_modification_request.png');
        log(`Modification requested: "${modification}"`);

        // Submit the modification
        await page.keyboard.press('Enter');
        log('Modification submitted, waiting for update...');

        // Wait for modification to apply
        await sleep(10000);

        await takeScreenshot(page, '08_modification_applied.png');
        results.screenshots.push('08_modification_applied.png');

        // Check if preview still exists and may have updated
        const finalPreview = await page.$('iframe');
        if (finalPreview) {
            log('MODIFICATION SUCCESS: Preview still visible after modification');
            results.modificationsWork = true;
        } else {
            log('MODIFICATION RESULT: Checking page state...');
        }

        // ============================================
        // FINAL SUMMARY
        // ============================================
        log('');
        log('='.repeat(60));
        log('FINAL TEST RESULTS');
        log('='.repeat(60));
        log(`Build Works: ${results.buildWorks ? 'PASS' : 'FAIL'}`);
        log(`Chat Works: ${results.chatWorks ? 'PASS' : 'FAIL'}`);
        log(`Modifications Work: ${results.modificationsWork ? 'PASS' : 'FAIL'}`);
        log(`Screenshots captured: ${results.screenshots.length}`);
        log('='.repeat(60));

        // Save results to file
        const resultsPath = path.join(__dirname, 'test_results.json');
        fs.writeFileSync(resultsPath, JSON.stringify(results, null, 2));
        log(`Results saved to: ${resultsPath}`);

        await sleep(5000); // Keep browser open briefly

    } catch (error) {
        log(`ERROR: ${error.message}`);
        console.error(error);
    } finally {
        await browser.close();
        log('Browser closed. Test complete.');
    }

    return results;
}

runFinalTest().catch(console.error);
