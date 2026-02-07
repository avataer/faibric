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
    console.log('FAIBRIC FINAL CUSTOMER TEST v3');
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

    let page;
    try {
        page = await browser.newPage();

        // Enable console logging
        page.on('console', msg => {
            const text = msg.text();
            if (!text.includes('React DevTools') && !text.includes('Future Flag') && !text.includes('[vite]')) {
                log(`[BROWSER] ${text}`);
            }
        });

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

        // Find and fill the textarea
        const textareaSelector = 'textarea';
        await page.waitForSelector(textareaSelector, { timeout: 10000 });

        const buildRequest = 'Create a modern landing page for a coffee shop called "Bean There" with a hero section, menu section, and contact form';
        await page.type(textareaSelector, buildRequest);
        await sleep(500);

        await takeScreenshot(page, '02_initial_request.png');
        results.screenshots.push('02_initial_request.png');
        log('Initial request entered');

        // Click the "Start Building" button - find by text content
        const clicked = await page.evaluate(() => {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.innerText.includes('Start Building')) {
                    btn.click();
                    return true;
                }
            }
            return false;
        });

        if (clicked) {
            log('Clicked "Start Building" button');
        } else {
            log('ERROR: Could not find Start Building button');
        }

        await sleep(3000);
        await takeScreenshot(page, '03_building.png');
        results.screenshots.push('03_building.png');

        // Wait for build to complete (look for iframe or preview)
        log('Waiting for build to complete...');
        let buildComplete = false;
        let attempts = 0;
        const maxAttempts = 120; // 2 minutes max

        while (!buildComplete && attempts < maxAttempts) {
            await sleep(1000);
            attempts++;

            // Check for iframe (preview)
            const iframe = await page.$('iframe');
            if (iframe) {
                buildComplete = true;
                log('Preview iframe detected!');
                break;
            }

            // Check URL - did we navigate away from landing?
            const currentUrl = page.url();
            if (currentUrl !== FRONTEND_URL && currentUrl !== FRONTEND_URL + '/') {
                log(`Navigated to: ${currentUrl}`);
            }

            if (attempts % 15 === 0) {
                log(`Still waiting... ${attempts}s elapsed`);
                await takeScreenshot(page, `03_building_${attempts}s.png`);
            }
        }

        await sleep(3000);
        await takeScreenshot(page, '04_build_complete.png');
        results.screenshots.push('04_build_complete.png');

        // Check current URL
        const currentUrl = page.url();
        log(`Current URL: ${currentUrl}`);

        // Check if build was successful
        const hasPreview = await page.$('iframe');
        const pageText = await page.evaluate(() => document.body.innerText);

        if (hasPreview) {
            log('BUILD SUCCESS: Preview iframe is visible');
            results.buildWorks = true;
        } else if (currentUrl !== FRONTEND_URL && currentUrl !== FRONTEND_URL + '/') {
            log('Navigation occurred - on builder page');
            // May still be building or have a different UI state
            if (pageText.toLowerCase().includes('building') || pageText.toLowerCase().includes('generating')) {
                log('BUILD: Still in progress');
            }
        } else {
            log('BUILD: Checking page state');
        }

        // Log visible text (first 800 chars)
        log('Page text: ' + pageText.substring(0, 800).replace(/\n/g, ' | '));

        // ============================================
        // TEST 3: CHAT/QUESTION FUNCTIONALITY
        // ============================================
        log('TEST 3: Testing chat functionality...');
        await sleep(2000);

        // Look for input field
        let chatInput = await page.$('input[type="text"]');
        if (!chatInput) {
            chatInput = await page.$('textarea');
        }

        if (chatInput) {
            // Clear existing content
            await chatInput.click({ clickCount: 3 });
            await page.keyboard.press('Backspace');
            await sleep(200);

            const question = 'What colors would work for this site?';
            await chatInput.type(question);
            await sleep(500);

            await takeScreenshot(page, '05_question_asked.png');
            results.screenshots.push('05_question_asked.png');
            log(`Question typed: "${question}"`);

            // Press Enter to submit
            await page.keyboard.press('Enter');
            log('Pressed Enter to submit question');

            // Wait for response
            log('Waiting for response...');
            await sleep(12000);

            await takeScreenshot(page, '06_conversation_response.png');
            results.screenshots.push('06_conversation_response.png');

            // Check response
            const responseText = await page.evaluate(() => document.body.innerText);
            log('Response preview: ' + responseText.substring(0, 600).replace(/\n/g, ' | '));

            // Check for conversation response indicators
            const lowerText = responseText.toLowerCase();
            if (lowerText.includes('starting fresh') ||
                (lowerText.includes('building') && lowerText.includes('new'))) {
                log('CHAT FAILED: Got rebuild response instead of conversation');
                results.chatWorks = false;
            } else if (lowerText.includes('color') ||
                       lowerText.includes('palette') ||
                       lowerText.includes('brown') ||
                       lowerText.includes('warm') ||
                       lowerText.includes('coffee') ||
                       lowerText.includes('recommend') ||
                       lowerText.includes('suggest')) {
                log('CHAT SUCCESS: Got conversational response');
                results.chatWorks = true;
            } else {
                log('CHAT RESULT: Response type unclear');
            }
        } else {
            log('No input field found for chat test');
        }

        // ============================================
        // TEST 4: MODIFICATION FUNCTIONALITY
        // ============================================
        log('TEST 4: Testing modification functionality...');
        await sleep(2000);

        // Find input again
        let modInput = await page.$('input[type="text"]');
        if (!modInput) {
            modInput = await page.$('textarea');
        }

        if (modInput) {
            await modInput.click({ clickCount: 3 });
            await page.keyboard.press('Backspace');
            await sleep(200);

            const modification = 'Make the header darker';
            await modInput.type(modification);
            await sleep(500);

            await takeScreenshot(page, '07_modification_request.png');
            results.screenshots.push('07_modification_request.png');
            log(`Modification typed: "${modification}"`);

            // Submit
            await page.keyboard.press('Enter');
            log('Submitted modification request');

            // Wait for modification to apply
            await sleep(15000);

            await takeScreenshot(page, '08_modification_applied.png');
            results.screenshots.push('08_modification_applied.png');

            // Check if preview exists
            const finalPreview = await page.$('iframe');
            if (finalPreview) {
                log('MODIFICATION SUCCESS: Preview visible after modification');
                results.modificationsWork = true;
            } else {
                const finalText = await page.evaluate(() => document.body.innerText);
                log('Final page state: ' + finalText.substring(0, 400).replace(/\n/g, ' | '));
            }
        } else {
            log('No input field found for modification test');
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

        await sleep(5000);

    } catch (error) {
        log(`ERROR: ${error.message}`);
        console.error(error);
        if (page) {
            await takeScreenshot(page, 'error_final.png');
        }
    } finally {
        await browser.close();
        log('Browser closed. Test complete.');
    }

    return results;
}

runFinalTest().catch(console.error);
