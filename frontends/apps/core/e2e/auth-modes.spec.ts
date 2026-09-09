import { expect, test, type Page } from "@playwright/test";
import { runFixture } from "./fixture";

// Run this spec after restarting CORE with the matching environment setting.
// It never changes live configuration and its fixture rejects SMTP backends.
const passwordMode = process.env.CORE_E2E_AUTH_PASSWORD_MODE ?? "required";
if (!["required", "optional", "passwordless"].includes(passwordMode)) {
  throw new Error("CORE_E2E_AUTH_PASSWORD_MODE must be required, optional or passwordless.");
}

async function signIn(page: Page, source: string) {
  await page.goto(`/accounts/login/?next=${encodeURIComponent(`/app/?source=${source}`)}`);
  await page.locator('[name="login"]').fill("core_e2e_qa@example.invalid");
  if (passwordMode === "passwordless") {
    await expect(page.locator('[name="password"]')).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Забыли пароль?" })).toHaveCount(0);
    await page.locator('form[action="/accounts/login/"] button[type="submit"]').click();
    await expect(page.locator('[name="code"]')).toBeVisible();
    expect((await (await page.request.get("/api/session/")).json()).authenticated).toBe(false);
    await page.locator('[name="code"]').fill(runFixture("login-mail").code as string);
    await page.locator('[name="code"]').press("Enter");
  } else {
    await page.locator('[name="password"]').fill(process.env.CORE_E2E_PASSWORD!);
    await page.locator('[name="password"]').press("Enter");
  }
  await expect(page).toHaveURL(new RegExp(`/app/\\?source=${source}$`));
  expect((await (await page.request.get("/api/session/")).json()).authenticated).toBe(true);
}

test(`real ${passwordMode} forms preserve native submission and the return address`, async ({ page, browser }, testInfo) => {
  runFixture("reset");
  const capabilities = await (await page.request.get("/api/capabilities/")).json();
  expect(capabilities.passwordLoginEnabled).toBe(passwordMode !== "passwordless");
  if (capabilities.registrationEnabled) {
    await page.goto("/accounts/signup/");
    for (const field of ["first_name", "last_name", "email"]) {
      await expect(page.locator(`[name="${field}"]`)).toHaveAttribute("required", "");
    }
    if (passwordMode === "passwordless") {
      await expect(page.locator('[name="password1"], [name="password2"]')).toHaveCount(0);
    } else {
      for (const field of ["password1", "password2"]) {
        await expect(page.locator(`[name="${field}"]`)).toBeVisible();
        expect(await page.locator(`[name="${field}"]`).getAttribute("required") !== null).toBe(passwordMode === "required");
      }
    }
  }

  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await signIn(page, `mode-${passwordMode}`);
  await expect(page.getByRole("heading", { name: "Core E2E Fixture" })).toBeVisible();
  await page.goto("/accounts/");
  await expect(page.getByRole("heading", { name: "Пароль", exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath(`account-${passwordMode}.png`), fullPage: true });
  const noJS = await browser.newContext({ javaScriptEnabled: false });
  const fallback = await noJS.newPage();
  await signIn(fallback, `mode-${passwordMode}-no-js`);
  await fallback.goto("/accounts/");
  await expect(fallback.getByRole("heading", { name: "Аккаунт и безопасность", exact: true })).toBeVisible();
  await noJS.close();
  expect(errors).toEqual([]);
});

test("anonymous server forms follow enabled methods even without JavaScript", async ({ browser, request }) => {
  const capabilities = await (await request.get("/api/capabilities/")).json();
  const noJS = await browser.newContext({ javaScriptEnabled: false });
  const page = await noJS.newPage();
  await page.goto("/accounts/login/");
  expect(await page.getByRole("link", { name: "Создать аккаунт" }).count() > 0).toBe(capabilities.registrationEnabled);
  expect(await page.locator("#passkey_login").count() > 0).toBe(capabilities.passkeyLoginEnabled);
  expect(await page.getByRole("link", { name: "Телефон Telegram", exact: true }).count() > 0).toBe(capabilities.phoneCodeLoginEnabled);
  expect(await page.getByRole("link", { name: "Код из email", exact: true }).count() > 0).toBe(capabilities.emailCodeLoginEnabled && capabilities.passwordLoginEnabled);
  for (const provider of ["google", "github", "telegram"]) {
    expect(await page.locator(`.provider-form[action*="/${provider}/login/"]`).count() > 0).toBe(capabilities.providers.includes(provider));
  }
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  }
  await noJS.close();
});
