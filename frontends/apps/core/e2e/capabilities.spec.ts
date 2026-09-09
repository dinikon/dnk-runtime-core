import { expect, test } from "@playwright/test";

const enabledCapabilities = {
  registrationEnabled: true,
  passwordLoginEnabled: false,
  emailCodeLoginEnabled: true,
  phoneCodeLoginEnabled: false,
  passkeyLoginEnabled: true,
  passkeySignupEnabled: true,
  providers: [],
};

test("the server-rendered Hero waits for capabilities before offering signup", async ({ page, request }) => {
  const html = await (await request.get("/")).text();
  expect(html).toContain("dNiko Alpha — единый аккаунт для вашей работы");
  expect(html).not.toContain('href="/accounts/signup/?next=/app/"');

  let releaseCapabilities!: () => void;
  const delayedCapabilities = new Promise<void>((resolve) => { releaseCapabilities = resolve; });
  await page.route("**/api/session/", (route) => route.fulfill({ json: { authenticated: false, csrfToken: "" } }));
  await page.route("**/api/capabilities/", async (route) => {
    await delayedCapabilities;
    await route.fulfill({ json: enabledCapabilities });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "dNiko Alpha — единый аккаунт для вашей работы" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Создать аккаунт" })).toHaveCount(0);
  await expect(page.locator(".hero-actions").getByRole("link", { name: "Войти" })).toBeVisible();
  releaseCapabilities();
  await expect(page.getByRole("link", { name: "Создать аккаунт" })).toBeVisible();
});

test("disabled registration keeps the login action at mobile widths", async ({ page }) => {
  await page.route("**/api/session/", (route) => route.fulfill({ json: { authenticated: false, csrfToken: "" } }));
  await page.route("**/api/capabilities/", (route) => route.fulfill({ json: { ...enabledCapabilities, registrationEnabled: false, passkeySignupEnabled: false } }));
  await page.goto("/");
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(page.getByRole("link", { name: "Создать аккаунт" })).toHaveCount(0);
    await expect(page.locator(".hero-actions").getByRole("link", { name: "Войти" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
});

test("capabilities failure can be retried without clearing a signed-in session", async ({ page }) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.route("**/api/session/", (route) => route.fulfill({ json: { authenticated: true, csrfToken: "" } }));
  await page.route("**/api/me/", (route) => route.fulfill({ json: {
    id: "a6d64c44-2316-4658-8b69-6d650da063a4", username: "capabilities_qa", email: "capabilities@example.test", first_name: "Capabilities", last_name: "QA",
  } }));
  let attempts = 0;
  await page.route("**/api/capabilities/", (route) => {
    attempts += 1;
    return attempts === 1
      ? route.fulfill({ status: 503, body: "temporarily unavailable" })
      : route.fulfill({ json: enabledCapabilities });
  });
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Открыть приложение" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Не удалось загрузить доступные способы входа");
  await page.getByRole("button", { name: "Повторить загрузку способов входа" }).click();
  await expect(page.getByRole("status")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Открыть приложение" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Создать аккаунт" })).toHaveCount(0);
  expect(attempts).toBe(2);
  expect(browserErrors).toEqual([]);
});
