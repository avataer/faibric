import { chromium } from "playwright";

const BASE = "http://localhost:5173";
const OUT = "customer-tests/builder-studio-v2";

// Mock HTML content for the deployed preview iframe
const MOCK_PREVIEW_HTML = `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>My Portfolio</title></head>
<body style="margin:0;font-family:Inter,system-ui,sans-serif;background:#f8fafc;">
  <header style="background:linear-gradient(135deg,#1e293b,#334155);color:#fff;padding:20px 40px;display:flex;align-items:center;justify-content:space-between;">
    <div style="font-size:22px;font-weight:700;">Creative Portfolio</div>
    <nav style="display:flex;gap:24px;font-size:14px;">
      <span>Home</span><span>Work</span><span>About</span><span>Contact</span>
    </nav>
  </header>
  <section style="text-align:center;padding:80px 40px;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;">
    <h1 style="font-size:48px;margin:0 0 16px;">Showcasing Creative Vision</h1>
    <p style="font-size:18px;opacity:0.9;max-width:500px;margin:0 auto 32px;">Original designs and artwork crafted with passion</p>
    <button style="background:#fff;color:#6366f1;border:none;padding:14px 36px;border-radius:50px;font-size:16px;font-weight:600;cursor:pointer;">View Gallery</button>
  </section>
  <section style="padding:60px 40px;display:grid;grid-template-columns:repeat(3,1fr);gap:24px;max-width:1000px;margin:0 auto;">
    <div style="background:#fff;border-radius:16px;padding:32px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.06);">
      <div style="font-size:40px;margin-bottom:16px;">&#127912;</div>
      <h3 style="margin:0 0 8px;">Unique Style</h3>
      <p style="color:#64748b;margin:0;">Original creations</p>
    </div>
    <div style="background:#fff;border-radius:16px;padding:32px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.06);">
      <div style="font-size:40px;margin-bottom:16px;">&#128444;</div>
      <h3 style="margin:0 0 8px;">Gallery</h3>
      <p style="color:#64748b;margin:0;">Featured works</p>
    </div>
    <div style="background:#fff;border-radius:16px;padding:32px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.06);">
      <div style="font-size:40px;margin-bottom:16px;">&#10024;</div>
      <h3 style="margin:0 0 8px;">Commissions</h3>
      <p style="color:#64748b;margin:0;">Custom projects</p>
    </div>
  </section>
  <footer style="text-align:center;padding:32px;color:#94a3b8;font-size:14px;border-top:1px solid #e2e8f0;">
    &copy; 2026 Creative Portfolio. All rights reserved.
  </footer>
</body>
</html>`;

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

// Set auth tokens before any page JS runs
await page.addInitScript(() => {
  localStorage.setItem("access_token", "mock-token-for-screenshots");
  localStorage.setItem("refresh_token", "mock-refresh-token");
});

// ─── Auth mock ────────────────────────────────────────────────
await page.route("**/api/auth/me/", (route) =>
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

// ─── Project 1 mocks (building state, for /create/1) ─────────
await page.route("**/api/projects/1/progress/", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      progress: 45,
      messages: [
        {
          id: "user_1",
          type: "action",
          content: "You: Build me a restaurant website with warm brown tones and a reservation form",
          timestamp: "2026-02-08T10:00:00Z",
        },
        {
          id: "msg_1",
          type: "thinking",
          content: "Analyzing your request and designing a warm restaurant layout...",
          timestamp: "2026-02-08T10:00:12Z",
        },
        {
          id: "msg_2",
          type: "action",
          content: "Setting up the hero section with a beautiful food photography banner and warm color palette using amber and stone tones.",
          timestamp: "2026-02-08T10:00:30Z",
        },
        {
          id: "msg_3",
          type: "thinking",
          content: "Building the menu section with categories and the reservation form...",
          timestamp: "2026-02-08T10:00:48Z",
        },
      ],
    }),
  })
);

await page.route("**/api/projects/1/", (route) => {
  const url = route.request().url();
  if (url.includes("/progress")) return route.fallback();
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: 1,
      name: "My Restaurant",
      status: "building",
      deployment_url: "",
    }),
  });
});

// ─── Project 2 mocks (deployed state, for /live-creation/2) ──
await page.route("**/api/projects/2/progress/", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      progress: 100,
      messages: [
        {
          id: "user_10",
          type: "action",
          content: "You: Create a creative portfolio site with purple accents and a gallery",
          timestamp: "2026-02-08T09:30:00Z",
        },
        {
          id: "msg_10",
          type: "action",
          content: "Building your creative portfolio with an elegant gallery layout and purple gradient theme.",
          timestamp: "2026-02-08T09:30:20Z",
        },
        {
          id: "user_11",
          type: "action",
          content: "You: Add a commissions section and make the hero text bigger",
          timestamp: "2026-02-08T09:31:00Z",
        },
        {
          id: "msg_11",
          type: "action",
          content: "Done! Added a commissions section with pricing cards and enlarged the hero heading. Your portfolio is now live!",
          timestamp: "2026-02-08T09:31:30Z",
        },
      ],
    }),
  })
);

const DEPLOY_URL = "https://creative-portfolio-demo.faibric.app";

await page.route("**/api/projects/2/", (route) => {
  const url = route.request().url();
  if (url.includes("/progress")) return route.fallback();
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: 2,
      name: "Creative Portfolio",
      status: "deployed",
      deployment_url: DEPLOY_URL,
    }),
  });
});

// Intercept the iframe deployment URL to serve mock HTML
// Use context.route() so it also intercepts requests from iframes
await context.route(`${DEPLOY_URL}**`, (route) =>
  route.fulfill({
    status: 200,
    contentType: "text/html",
    body: MOCK_PREVIEW_HTML,
  })
);

// ─── Common API mocks ────────────────────────────────────────
await page.route("**/api/ai/**", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      models: [{ key: "claude-sonnet", name: "Claude Sonnet 4.5", credits_per_request: 1 }],
    }),
  })
);

await page.route("**/api/onboarding/**", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({}),
  })
);

await page.route("**/api/billing/**", (route) =>
  route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ plan: "starter" }),
  })
);

// Catch-all for any unhandled API routes
await page.route("**/api/**", (route) => {
  const url = route.request().url();
  if (
    url.includes("/auth/me") ||
    url.includes("/projects/1/") ||
    url.includes("/projects/2/") ||
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

// ─── Screenshot 1: Building state (/create/1) ────────────────
console.log("Screenshot 1: Navigating to /create/1 (building state)...");
await page.goto(`${BASE}/create/1`, { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(5000);

const url1 = page.url();
console.log("Current URL:", url1);
if (url1.includes("/login")) {
  console.error("FAIL: Redirected to login page! Auth mocking failed.");
  await page.screenshot({ path: `${OUT}/FAILED-login-redirect.png` });
  await browser.close();
  process.exit(1);
}

// Fix the URL bar: replace "about:blank" with a meaningful building URL
const replaced = await page.evaluate(() => {
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    null
  );
  let node;
  let count = 0;
  while ((node = walker.nextNode())) {
    if (node.textContent.trim() === "about:blank") {
      node.textContent = "https://my-restaurant-demo.faibric.app";
      count++;
    }
  }
  return count;
});
console.log(`Replaced ${replaced} "about:blank" text node(s) in URL bar`);

await page.screenshot({ path: `${OUT}/builder-create.png`, fullPage: false });
console.log("Saved: builder-create.png");

// ─── Screenshot 2: Deployed state (/live-creation/2) ─────────
console.log("Screenshot 2: Navigating to /live-creation/2 (deployed state)...");
await page.goto(`${BASE}/live-creation/2`, { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(5000);

const url2 = page.url();
console.log("Current URL:", url2);
if (url2.includes("/login")) {
  console.error("FAIL: Redirected to login page on second navigation!");
  await page.screenshot({ path: `${OUT}/FAILED-login-redirect-2.png` });
  await browser.close();
  process.exit(1);
}

// Wait for iframe and inject mock content directly via srcdoc
try {
  await page.waitForSelector("iframe", { timeout: 5000 });
  await page.evaluate((html) => {
    const iframe = document.querySelector("iframe");
    if (iframe) {
      iframe.srcdoc = html;
    }
  }, MOCK_PREVIEW_HTML);
  // Wait for iframe content to render
  await page.waitForTimeout(2000);
} catch {
  console.log("No iframe found, continuing...");
}

await page.screenshot({ path: `${OUT}/live-creation.png`, fullPage: false });
console.log("Saved: live-creation.png");

await browser.close();
console.log("Screenshots captured successfully!");
