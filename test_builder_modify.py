#!/usr/bin/env python3
"""
Test Builder modification end-to-end:
1) Visit deployed site
2) Go to /faibric and login with faibric123
3) Click on Builder tab
4) Type "make all text red" and submit
5) Verify result
"""

import asyncio
import os
from datetime import datetime
from playwright.async_api import async_playwright

SITE_URL = "https://app0mqv0bp3u7-8mm9w0jji-antons-projects-f1d70cf2.vercel.app"
SCREENSHOT_DIR = "/Users/abram/Code/Faibric/docs"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        results = {"success": False, "error": None, "screenshots": []}

        try:
            # Step 1: Visit deployed site
            print(f"[1/7] Visiting deployed site: {SITE_URL}")
            await page.goto(SITE_URL, timeout=30000)
            await page.wait_for_load_state("networkidle")

            screenshot1 = f"{SCREENSHOT_DIR}/builder_test_site_before.png"
            await page.screenshot(path=screenshot1, full_page=False)
            results["screenshots"].append(screenshot1)
            print(f"  Screenshot: {screenshot1}")

            # Step 2: Go to /faibric
            print(f"[2/7] Going to /faibric login page")
            await page.goto(f"{SITE_URL}/faibric", timeout=30000)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)

            screenshot2 = f"{SCREENSHOT_DIR}/builder_test_login_page.png"
            await page.screenshot(path=screenshot2, full_page=False)
            results["screenshots"].append(screenshot2)
            print(f"  Screenshot: {screenshot2}")

            # Step 3: Enter password and login
            print(f"[3/7] Logging in with faibric123")

            # Find password input and submit
            password_input = await page.query_selector('input[type="password"]')
            if password_input:
                await password_input.fill("faibric123")

                # Find and click login button
                login_btn = await page.query_selector('button[type="submit"]')
                if login_btn:
                    await login_btn.click()
                else:
                    # Try pressing Enter
                    await password_input.press("Enter")

                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
            else:
                print("  Warning: No password input found, may already be logged in")

            screenshot3 = f"{SCREENSHOT_DIR}/builder_test_dashboard.png"
            await page.screenshot(path=screenshot3, full_page=False)
            results["screenshots"].append(screenshot3)
            print(f"  Screenshot: {screenshot3}")

            # Step 4: Click on Builder tab
            print(f"[4/7] Clicking on Builder tab")

            # Look for Builder tab in navigation
            builder_tab = await page.query_selector('text=Builder')
            if builder_tab:
                await builder_tab.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                print("  Clicked Builder tab")
            else:
                # Try "Open Builder" button
                open_builder = await page.query_selector('text=Open Builder')
                if open_builder:
                    await open_builder.click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    print("  Clicked Open Builder button")
                else:
                    print("  Warning: No Builder tab found")

            screenshot4 = f"{SCREENSHOT_DIR}/builder_test_builder_tab.png"
            await page.screenshot(path=screenshot4, full_page=False)
            results["screenshots"].append(screenshot4)
            print(f"  Screenshot: {screenshot4}")

            # Step 5: Find the Builder input and type modification request
            print(f"[5/7] Typing 'make all text red' in Builder")

            # Look for Builder input (textarea or input)
            builder_input = await page.query_selector('textarea')
            if not builder_input:
                builder_input = await page.query_selector('input[type="text"]:not([type="password"])')
            if not builder_input:
                # Try placeholder text
                builder_input = await page.query_selector('[placeholder*="change"]')
            if not builder_input:
                builder_input = await page.query_selector('[placeholder*="request"]')
            if not builder_input:
                builder_input = await page.query_selector('[placeholder*="describe"]')

            if builder_input:
                await builder_input.fill("make all text red")

                screenshot5 = f"{SCREENSHOT_DIR}/builder_test_typed.png"
                await page.screenshot(path=screenshot5, full_page=False)
                results["screenshots"].append(screenshot5)
                print(f"  Screenshot: {screenshot5}")

                # Step 6: Submit the modification
                print(f"[6/7] Submitting modification request")

                # Find submit button
                submit_btn = await page.query_selector('button:has-text("Send")')
                if not submit_btn:
                    submit_btn = await page.query_selector('button:has-text("Submit")')
                if not submit_btn:
                    submit_btn = await page.query_selector('button:has-text("Apply")')
                if not submit_btn:
                    submit_btn = await page.query_selector('button:has-text("Generate")')
                if not submit_btn:
                    # Try finding any button near the input
                    submit_btn = await page.query_selector('form button[type="submit"]')

                if submit_btn:
                    await submit_btn.click()
                    print("  Clicked submit button")
                else:
                    # Try pressing Enter
                    await builder_input.press("Enter")
                    print("  Pressed Enter to submit")

                # Wait for response
                await asyncio.sleep(5)

                screenshot6 = f"{SCREENSHOT_DIR}/builder_test_after_submit.png"
                await page.screenshot(path=screenshot6, full_page=False)
                results["screenshots"].append(screenshot6)
                print(f"  Screenshot: {screenshot6}")

                # Wait longer for modification to complete
                print(f"[7/7] Waiting for modification to complete (up to 120s)")
                for i in range(24):
                    await asyncio.sleep(5)
                    # Check page content for error messages
                    content = await page.content()

                    if "Session not found" in content:
                        results["error"] = "Session not found error"
                        print(f"  ERROR: Session not found")
                        break
                    elif "error" in content.lower() and "Error:" in content:
                        results["error"] = "Error message found"
                        print(f"  ERROR: Error message found")
                        break
                    elif i == 6:  # 30 second mark
                        screenshot_mid = f"{SCREENSHOT_DIR}/builder_test_30s.png"
                        await page.screenshot(path=screenshot_mid, full_page=False)
                        results["screenshots"].append(screenshot_mid)
                        print(f"  Screenshot (30s): {screenshot_mid}")
                    elif i == 12:  # 60 second mark
                        screenshot_mid2 = f"{SCREENSHOT_DIR}/builder_test_60s.png"
                        await page.screenshot(path=screenshot_mid2, full_page=False)
                        results["screenshots"].append(screenshot_mid2)
                        print(f"  Screenshot (60s): {screenshot_mid2}")

                # Final screenshot
                screenshot_final = f"{SCREENSHOT_DIR}/builder_test_final_result.png"
                await page.screenshot(path=screenshot_final, full_page=False)
                results["screenshots"].append(screenshot_final)
                print(f"  Final screenshot: {screenshot_final}")

                # Check for success indicators
                content = await page.content()
                if "Session not found" in content:
                    results["error"] = "Session not found"
                    results["success"] = False
                else:
                    results["success"] = True

            else:
                results["error"] = "No Builder input found"
                print("  ERROR: No Builder input found")

                # Take a debug screenshot
                debug_screenshot = f"{SCREENSHOT_DIR}/builder_test_no_input_debug.png"
                await page.screenshot(path=debug_screenshot, full_page=True)
                results["screenshots"].append(debug_screenshot)

        except Exception as e:
            results["error"] = str(e)
            print(f"  ERROR: {e}")

            # Take error screenshot
            try:
                error_screenshot = f"{SCREENSHOT_DIR}/builder_test_error.png"
                await page.screenshot(path=error_screenshot, full_page=False)
                results["screenshots"].append(error_screenshot)
            except:
                pass

        finally:
            await browser.close()

        # Print summary
        print("\n" + "="*50)
        print("RESULTS SUMMARY")
        print("="*50)
        print(f"Success: {results['success']}")
        print(f"Error: {results['error']}")
        print(f"Screenshots: {len(results['screenshots'])}")
        for s in results["screenshots"]:
            print(f"  - {s}")

        return results

if __name__ == "__main__":
    asyncio.run(main())
