import { chromium } from "playwright";

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

// Set auth tokens FIRST via addInitScript (runs before page JS)
await page.addInitScript(() => {
  localStorage.setItem("access_token", "mock-token-for-screenshots");
  localStorage.setItem("refresh_token", "mock-refresh-token");
});

// Mock ALL API routes BEFORE navigating
// Auth endpoint - must return valid user data to pass ProtectedRoute
await page.route("**/api/auth/me/", route =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: 1,
      username: "demo",
      email: "demo@test.com",
      is_staff: false,
    }),
  })
);

// Project progress endpoint with realistic chat messages
await page.route("**/api/projects/1/progress/", route =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      progress: 65,
      messages: [
        {
          id: "msg_1",
          type: "action",
          content: "Build me a restaurant website with warm brown tones",
          timestamp: "2025-01-15T10:00:00Z",
        },
        {
          id: "msg_2",
          type: "thinking",
          content: "Analyzing your request and designing the layout...",
          timestamp: "2025-01-15T10:00:15Z",
        },
        {
          id: "msg_3",
          type: "action",
          content: "Creating a warm, inviting restaurant website with hero section, menu, and reservation form",
          timestamp: "2025-01-15T10:00:30Z",
        },
        {
          id: "user_1",
          type: "action",
          content: "You: Make the header bigger and add a hero image",
          timestamp: "2025-01-15T10:01:00Z",
        },
        {
          id: "msg_4",
          type: "thinking",
          content: "Updating the header size and adding a beautiful hero image...",
          timestamp: "2025-01-15T10:01:15Z",
        },
        {
          id: "msg_5",
          type: "action",
          content: "Your restaurant website is looking great! The hero image really makes it pop.",
          timestamp: "2025-01-15T10:01:45Z",
        },
      ],
    }),
  })
);

// Project detail endpoint
await page.route("**/api/projects/1/", route => {
  // Don't intercept progress sub-routes
  const url = route.request().url();
  if (url.includes("/progress")) return route.fallback();
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: 1,
      name: "My Restaurant",
      status: "deployed",
      deployment_url: "https://my-restaurant-demo.faibric.app",
    }),
  });
});

// Catch-all API routes to prevent errors
await page.route("**/api/ai/**", route =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ models: [{ key: "claude-sonnet", name: "Claude Sonnet 4.5", credits_per_request: 1 }] }),
  })
);

await page.route("**/api/onboarding/**", route =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({}),
  })
);

await page.route("**/api/billing/**", route =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ plan: "starter" }),
  })
);

// Catch any remaining API calls
await page.route("**/api/**", route => {
  const url = route.request().url();
  // Let already-handled routes fall through
  if (
    url.includes("/auth/me") ||
    url.includes("/projects/1/progress") ||
    url.includes("/projects/1/") ||
    url.includes("/ai/") ||
    url.includes("/onboarding/") ||
    url.includes("/billing/")
  ) {
    return route.fallback();
  }
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({}),
  });
});

console.log("Navigating to /create/1 (LiveCreation page)...");
await page.goto("http://localhost:5173/create/1", { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(4000);

// Check URL - if redirected to login, something went wrong
const url1 = page.url();
console.log("Current URL:", url1);
if (url1.includes("/login")) {
  console.error("FAIL: Redirected to login page! Auth mocking did not work.");
  await page.screenshot({ path: "customer-tests/builder-studio-v2/FAILED-login-redirect.png" });
  await browser.close();
  process.exit(1);
}

await page.screenshot({
  path: "customer-tests/builder-studio-v2/builder-create.png",
  fullPage: false,
});
console.log("Screenshot saved: builder-create.png");

console.log("Navigating to /live-creation/1...");
await page.goto("http://localhost:5173/live-creation/1", { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(4000);

const url2 = page.url();
console.log("Current URL:", url2);
if (url2.includes("/login")) {
  console.error("FAIL: Redirected to login page on second navigation!");
  await page.screenshot({ path: "customer-tests/builder-studio-v2/FAILED-login-redirect-2.png" });
  await browser.close();
  process.exit(1);
}

await page.screenshot({
  path: "customer-tests/builder-studio-v2/live-creation.png",
  fullPage: false,
});
console.log("Screenshot saved: live-creation.png");

await browser.close();
console.log("Screenshots captured successfully!");
