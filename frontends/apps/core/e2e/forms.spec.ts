import { expect, test } from "@playwright/test";
import { runFixture } from "./fixture";

// Browser plugin not available in the tool catalog; Playwright also exposes CDP
// virtual authenticators, needed to test real WebAuthn without a personal key.
test("passkey signup, OTP paste, cancellation, recovery codes and safe return", async ({ page, context }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  const cdp = await context.newCDPSession(page);
  await cdp.send("WebAuthn.enable");
  const { authenticatorId } = await cdp.send("WebAuthn.addVirtualAuthenticator", { options: {
    protocol: "ctap2", transport: "internal", hasResidentKey: true, hasUserVerification: true,
    isUserVerified: true, automaticPresenceSimulation: true,
  } });
  await page.goto("/accounts/signup/passkey/?next=/app/?source=passkey-signup");
  await expect(page.locator('[name="password1"]')).toHaveCount(0);
  await expect(page.locator('[name="phone"]')).toHaveCount(0);
  const username = process.env.CORE_E2E_SIGNUP_USERNAME!;
  await expect(page.locator('[name="username"]')).toHaveCount(0);
  await page.locator('[name="last_name"]').fill("Passkey QA");
  await page.locator('[name="first_name"]').fill("Core E2E Signup");
  await page.locator('[name="middle_name"]').fill("Тест");
  await page.locator('[name="email"]').fill(`${username}@example.invalid`);
  await page.locator('[name="email"]').press("Enter");
  await expect(page).toHaveURL(/\/accounts\/confirm-email\//);
  await expect(page.locator('[data-slot="input-otp-slot"]')).toHaveCount(6);
  const code = runFixture("mail").code as string;
  // One input receives the complete pasted value; six visual slots mirror it.
  await page.locator('input[name="code"]').fill(code);
  await expect(page.locator('[data-slot="input-otp-slot"]').first()).toHaveText(code[0]!);
  await page.screenshot({ path: testInfo.outputPath("signup-email-code.png") });
  await page.locator('input[name="code"]').press("Enter");
  await expect(page).toHaveURL(/\/accounts\/2fa\/webauthn\/signup\//);
  expect((await (await page.request.get("/api/session/")).json()).authenticated).toBe(false);
  await page.evaluate(() => {
    const original = navigator.credentials.create.bind(navigator.credentials);
    navigator.credentials.create = () => { navigator.credentials.create = original; return Promise.reject(new DOMException("Cancelled by test", "NotAllowedError")); };
  });
  await page.locator("#mfa_webauthn_signup").click();
  await expect(page.locator("#webauthn-feedback")).toBeVisible();
  await expect(page.locator("#mfa_webauthn_signup")).toBeEnabled();
  expect((await (await page.request.get("/api/session/")).json()).authenticated).toBe(false);
  await page.locator('[name="name"]').fill("My virtual device");
  await page.locator("#mfa_webauthn_signup").click();
  await expect(page).toHaveURL(/\/accounts\/2fa\/recovery-codes\//);
  const codes = await page.locator("#recovery_codes").inputValue();
  expect(codes.match(/[0-9]{8}/g)?.length).toBeGreaterThan(0);
  const beforeUnloadDialogs: string[] = [];
  page.on("dialog", async dialog => { beforeUnloadDialogs.push(dialog.type()); await dialog.accept(); });
  await page.locator("#codes_saved_control").click();
  await expect(page.locator("#codes_saved")).toBeChecked();
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/\?source=passkey-signup$/);
  expect(beforeUnloadDialogs).toEqual([]);
  await expect(page.getByRole("heading", { name: "Passkey QA Core E2E Signup Тест", exact: true })).toBeVisible();
  const profile = await (await page.request.get("/api/me/")).json();
  expect(profile.username).toMatch(/^user_[a-f0-9]{32}$/);
  expect(profile.middle_name).toBe("Тест");
  await page.goto("/accounts/2fa/recovery-codes/");
  await expect(page.locator("#recovery_codes")).toHaveCount(0);
  const { credentials } = await cdp.send("WebAuthn.getCredentials", { authenticatorId });
  expect(credentials).toHaveLength(1);
  expect(credentials[0]?.isResidentCredential).toBe(true);
  expect(errors).toEqual([]);
});

test("server fallback, entered values, password reveal and mobile layout", async ({ browser, page }, testInfo) => {
  runFixture("reset");
  for (const path of ["/", "/accounts/signup/", "/accounts/signup/passkey/", "/accounts/password/reset/", "/accounts/login/code/?channel=email", "/accounts/login/code/?channel=telegram"]) {
    await page.goto(path);
    for (const width of [360, 390]) {
      await page.setViewportSize({ width, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
  }
  const noJS = await browser.newContext({ javaScriptEnabled: false });
  const fallback = await noJS.newPage();
  await fallback.goto("/accounts/login/?next=/app/?source=no-js");
  await fallback.locator('[name="login"]').fill("core_e2e_qa@example.invalid");
  await fallback.locator('[name="password"]').fill(process.env.CORE_E2E_PASSWORD!);
  await fallback.locator('form[action="/accounts/login/"] button[type="submit"]').click();
  await expect(fallback).toHaveURL(/\/app\/\?source=no-js$/);
  await fallback.goto("/accounts/");
  await expect(fallback.getByRole("heading", { name: "Аккаунт и безопасность", exact: true })).toBeVisible();
  await noJS.close();

  await page.route("**/static/core/ui/assets/*.js", async route => {
    await new Promise(resolve => setTimeout(resolve, 1500)); await route.continue();
  }, { times: 1 });
  await page.goto("/accounts/login/?next=/app/?source=forms", { waitUntil: "commit" });
  await page.locator('[name="login"]').fill("core_e2e_qa@example.invalid");
  await page.locator('[name="password"]').fill("incorrect password");
  await page.waitForFunction(() => document.querySelector('[data-slot="input-group"]'));
  await expect(page.locator('[name="login"]')).toHaveValue("core_e2e_qa@example.invalid");
  await expect(page.locator('[name="password"]')).toHaveValue("incorrect password");
  await expect(page.locator('[name="password"]')).toBeFocused();
  await page.getByRole("button", { name: "Показать пароль" }).click();
  await expect(page.locator('[name="password"]')).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Скрыть пароль" }).click();
  await page.locator('[name="password"]').press("Enter");
  await expect(page.locator(".form-errors")).toBeVisible();
  await expect(page.locator('[name="login"]')).toHaveValue("core_e2e_qa@example.invalid");
  await expect(page.locator('[name="password"]')).toHaveValue("");
  await expect(page.locator('form[action="/accounts/login/"] [name="next"]')).toHaveValue("/app/?source=forms");
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`login-error-${width}.png`), fullPage: true });
  }
  await page.locator('[name="password"]').fill(process.env.CORE_E2E_PASSWORD!);
  await page.locator('[name="password"]').press("Enter");
  await expect(page).toHaveURL(/\/app\/\?source=forms$/);
  await page.goto("/accounts/");
  await page.getByRole("button", { name: "Аккаунт и безопасность", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("button", { name: "Закрыть меню" })).toBeInViewport();
  const closeButton = await page.getByRole("button", { name: "Закрыть меню" }).boundingBox();
  expect(closeButton?.width).toBeGreaterThanOrEqual(44);
  expect(closeButton?.height).toBeGreaterThanOrEqual(44);
  await page.screenshot({ path: testInfo.outputPath("account-mobile-menu.png"), animations: "disabled" });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Аккаунт и безопасность", exact: true })).toBeFocused();
});

test("security pages keep named actions, keyboard submission and responsive fields", async ({ page }, testInfo) => {
  runFixture("reset");
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/accounts/login/");
  await page.locator('[name="login"]').fill("core_e2e_qa@example.invalid");
  await page.locator('[name="password"]').fill(process.env.CORE_E2E_PASSWORD!);
  await page.locator('[name="password"]').press("Enter");
  await expect(page).toHaveURL(/\/app\/$/);
  await page.goto("/accounts/email/");
  let submits = 0;
  page.on("request", request => { if (request.method() === "POST" && new URL(request.url()).pathname === "/accounts/email/") submits += 1; });
  const request = page.waitForRequest(request => request.method() === "POST" && new URL(request.url()).pathname === "/accounts/email/");
  await page.locator('button[name="action_primary"]').evaluate((button: HTMLButtonElement) => {
    button.form!.requestSubmit(button); button.form!.requestSubmit(button);
  });
  const data = new URLSearchParams((await request).postData()!);
  expect(data.has("action_primary")).toBe(true);
  expect(data.has("action_remove")).toBe(false);
  await expect(page.locator('button[name="action_primary"]')).toBeEnabled();
  expect(submits).toBe(1);
  for (const path of ["/accounts/", "/accounts/email/", "/accounts/password/change/", "/accounts/3rdparty/", "/accounts/2fa/", "/accounts/2fa/webauthn/", "/accounts/sessions/"]) {
    await page.goto(path);
    await expect(page.locator("main h1")).toBeVisible();
    for (const width of [360, 390, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
    if (path === "/accounts/") await page.screenshot({ path: testInfo.outputPath("account-security-desktop.png"), fullPage: true });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/accounts/");
  await page.screenshot({ path: testInfo.outputPath("account-security-mobile.png"), fullPage: true });
  expect(errors).toEqual([]);
});
