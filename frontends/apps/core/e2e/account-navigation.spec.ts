import { expect, test, type Page } from "@playwright/test";
import { runFixture } from "./fixture";

// Browser plugin is unavailable; these isolated Playwright scenarios only use
// marked local fixtures and never invoke real OAuth or mail providers.
async function signIn(page: Page) {
  await page.goto("/accounts/login/?next=/app/");
  await page.locator('[name="login"]').fill("core_e2e_qa");
  await page.locator('[name="password"]').fill(process.env.CORE_E2E_PASSWORD!);
  await page.locator('[name="password"]').press("Enter");
  await expect(page).toHaveURL(/\/app\/$/);
  await expect(page.getByRole("heading", { name: "Core E2E Fixture" })).toBeVisible();
}

test("admin navigation follows actual staff and superuser roles in Nuxt and Django", async ({ page }, testInfo) => {
  runFixture("reset");
  await signIn(page);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  try {
    for (const role of ["member", "staff", "superuser"] as const) {
      runFixture("navigation", { role });
      const session = await (await page.request.get("/api/session/")).json();
      expect(session.showAdminLink).toBe(role !== "member");
      for (const path of ["/app/", "/accounts/"]) {
        await page.goto(path);
        const adminLink = page.locator(".site-header").getByRole("link", { name: "Django admin", exact: true });
        for (const width of [1440, 360, 390]) {
          await page.setViewportSize({ width, height: 900 });
          if (role === "member") {
            await expect(adminLink).toHaveCount(0);
          } else {
            await expect(adminLink).toBeVisible();
            await expect(adminLink).toHaveAttribute("href", "/admin/");
            await expect(adminLink).toBeInViewport();
          }
          expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        }
        if (role === "staff") {
          await page.screenshot({ path: testInfo.outputPath(path === "/app/" ? "nuxt-admin-mobile.png" : "django-admin-mobile.png"), fullPage: true });
        }
      }
      const admin = await page.request.get("/admin/", { maxRedirects: 0 });
      // A superuser-only navigation hint does not bypass Django's is_staff gate.
      expect(admin.status()).toBe(role === "staff" ? 200 : 302);
    }
  } finally {
    runFixture("navigation", { role: "member" });
  }
  expect(errors).toEqual([]);
});

test("saved social identities are readable and empty recovery codes never generate on GET", async ({ page, browser }, testInfo) => {
  runFixture("reset");
  runFixture("navigation", { role: "member" });
  await signIn(page);
  const labels = ["GitHub · @core_qa_github", "Telegram · @core_qa_telegram", "Google · core_qa_google@example.invalid"];
  for (const path of ["/accounts/", "/accounts/3rdparty/"]) {
    await page.goto(path);
    for (const label of labels) await expect(page.getByText(label, { exact: true })).toBeVisible();
    expect(await page.locator("main").innerText()).not.toContain("core-e2e-github-");
  }
  expect(runFixture("inspect").recovery_authenticators).toBe(0);
  for (let visit = 0; visit < 2; visit += 1) {
    const response = await page.goto("/accounts/2fa/recovery-codes/");
    expect(response?.status()).toBe(200);
    await expect(page.getByRole("heading", { name: "Резервные коды", exact: true })).toBeVisible();
    await expect(page.getByText("Сначала подключите приложение-аутентификатор", { exact: false })).toBeVisible();
    await expect(page.locator("#recovery_codes")).toHaveCount(0);
  }
  expect(runFixture("inspect").recovery_authenticators).toBe(0);
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.screenshot({ path: testInfo.outputPath("empty-recovery-mobile.png"), fullPage: true });
  const noJS = await browser.newContext({ javaScriptEnabled: false, storageState: await page.context().storageState() });
  const fallback = await noJS.newPage();
  expect((await fallback.goto("/accounts/2fa/recovery-codes/"))?.status()).toBe(200);
  await expect(fallback.getByRole("heading", { name: "Резервные коды", exact: true })).toBeVisible();
  await fallback.goto("/accounts/3rdparty/");
  for (const label of labels) await expect(fallback.getByText(label, { exact: true })).toBeVisible();
  await noJS.close();
  expect(runFixture("inspect").recovery_authenticators).toBe(0);
});
