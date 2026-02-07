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
    console.log('FAIBRIC FINAL CUSTOMER TEST v2');
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
        page.on('console', msg => {
            const text = msg.text();
            if (!text.includes('React DevTools') && !text.includes('Future Flag')) {
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

        // Click the "Start Building" button
        const startBuildingButton = await page.$('button');
        if (startBuildingButton) {
            const buttonText = await page.evaluate(el => el.innerText, startBuildingButton);
            log(`Found button: "${buttonText}"`);
            await startBuildingButton.click();
            log('Clicked Start Building button');
        } else {
            log('ERROR: Start Building button not found');
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

            // Check for error messages in page content
            const pageContent = await page.content();
            if (pageContent.toLowerCase().includes('error') &&
                (pageContent.includes('database') || pageContent.includes('500'))) {
                log('ERROR: Database/Server error detected!');
                await takeScreenshot(page, `error_at_${attempts}s.png`);
                break;
            }

            // Check for chat interface (which would indicate we're past landing)
            const hasChatInterface = await page.$('.chat-messages, .message-list, [class*="chat"], [class*="message"]');
            if (hasChatInterface) {
                log('Chat interface detected - build may be in progress');
            }

            if (attempts % 15 === 0) {
                log(`Still waiting... ${attempts}s elapsed`);
                await takeScreenshot(page, `03_building_${attempts}s.png`);
            }
        }

        await sleep(3000);
        await takeScreenshot(page, '04_build_complete.png');
        results.screenshots.push('04_build_complete.png');

        // Check current URL to see if we navigated
        const currentUrl = page.url();
        log(`Current URL: ${currentUrl}`);

        // Check if build was successful
        const hasPreview = await page.$('iframe');
        const pageText = await page.evaluate(() => document.body.innerText);

        if (hasPreview) {
            log('BUILD SUCCESS: Preview iframe is visible');
            results.buildWorks = true;
        } else if (currentUrl !== FRONTEND_URL && currentUrl !== FRONTEND_URL + '/') {
            log('Navigation occurred - checking page state');
            // Check if there's a chat interface or project view
            if (pageText.includes('error') || pageText.includes('Error')) {
                log('BUILD FAILED: Error visible on page');
            } else {
                log('BUILD: In progress or different state');
            }
        } else {
            log('BUILD FAILED: Still on landing page');
        }

        // Log what's on the page
        log('Page content preview: ' + pageText.substring(0, 500).replace(/\n/g, ' '));

        // ============================================
        // TEST 3: CHAT/QUESTION FUNCTIONALITY
        // ============================================
        log('TEST 3: Testing chat functionality...');
        await sleep(2000);

        // Look for input field (might be different after build)
        let chatInput = await page.$('input[type="text"]');
        if (!chatInput) {
            chatInput = await page.$('textarea');
        }
        if (!chatInput) {
            chatInput = await page.$('[contenteditable="true"]');
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

            // Look for send button or press Enter
            const sendButton = await page.$('button[type="submit"], button:has-text("Send"), button:has-text("Ask")');
            if (sendButton) {
                await sendButton.click();
                log('Clicked send button');
            } else {
                await page.keyboard.press('Enter');
                log('Pressed Enter to submit');
            }

            // Wait for response
            log('Waiting for response...');
            await sleep(10000);

            await takeScreenshot(page, '06_conversation_response.png');
            results.screenshots.push('06_conversation_response.png');

            // Check response
            const responseText = await page.evaluate(() => document.body.innerText);
            log('Response content preview: ' + responseText.substring(0, 500).replace(/\n/g, ' '));

            if (responseText.includes('Starting fresh') || responseText.includes('Building')) {
                log('CHAT FAILED: Got rebuild response instead of conversation');
                results.chatWorks = false;
            } else if (responseText.toLowerCase().includes('color') ||
                       responseText.toLowerCase().includes('palette') ||
                       responseText.toLowerCase().includes('brown') ||
                       responseText.toLowerCase().includes('warm')) {
                log('CHAT SUCCESS: Got conversational response about colors');
                results.chatWorks = true;
            } else {
                log('CHAT RESULT: Checking response type...');
                // Still might be successful, just different keywords
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

            // Check if preview still exists
            const finalPreview = await page.$('iframe');
            if (finalPreview) {
                log('MODIFICATION SUCCESS: Preview still visible after modification');
                results.modificationsWork = true;
            } else {
                log('MODIFICATION RESULT: Checking final state...');
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
        await takeScreenshot(page, 'error_final.png');
    } finally {
        await browser.close();
        log('Browser closed. Test complete.');
    }

    return results;
}

runFinalTest().catch(console.error);
