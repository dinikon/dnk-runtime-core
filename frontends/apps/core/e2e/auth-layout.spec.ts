import { expect, test } from "@playwright/test";
import { runFixture } from "./fixture";

// Browser plugin not available. Use the existing isolated Playwright stack.
const passwordMode = process.env.CORE_E2E_AUTH_PASSWORD_MODE ?? "required";

test("channel segments preserve native fields, focus and return addresses", async ({ page, browser }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/accounts/login/?next=%2Fapp%2F%3Fsource%3Dchannels%26nested%3Dyes");
  const capabilities = await (await page.request.get("/api/capabilities/")).json();
  await expect(page).toHaveTitle(/Войти.*dNiko Alpha/);
  await expect(page.locator(".auth-brand")).toBeVisible();
  await expect(page.locator(".site-header, .site-footer")).toHaveCount(0);
  await expect(page.locator(".auth-card")).toBeVisible();
  await page.waitForFunction("window.coreUIState === 'ready'");
  const panels = page.locator("[data-login-panel]");
  const email = panels.locator('input[name="login"]');
  await email.fill("draft@example.invalid");
  let posts = 0;
  page.on("request", request => { if (request.method() === "POST") posts += 1; });
  if (capabilities.phoneCodeLoginEnabled) {
    const phoneToggle = page.getByRole("button", { name: "Телефон Telegram", exact: true });
    const emailToggle = page.getByRole("button", { name: "Email", exact: true });
    await phoneToggle.click();
    await expect(page.locator('[name="phone"]')).toBeVisible();
    await page.locator('[name="phone"]').fill("+380501234567");
    await emailToggle.click();
    await expect(email).toHaveValue("draft@example.invalid");
    await emailToggle.click();
    await expect(emailToggle).toHaveAttribute("aria-pressed", "true");
    await expect(email).toBeVisible();
    await emailToggle.focus();
    await page.keyboard.press("ArrowRight");
    await expect(phoneToggle).toBeFocused();
    await page.keyboard.press("Space");
    await expect(page.locator('[name="phone"]')).toHaveValue("+380501234567");
    expect(posts).toBe(0);
    expect(new URL(page.url()).searchParams.get("next")).toBe("/app/?source=channels&nested=yes");
    await page.locator('[name="phone"]').fill("invalid");
    const posted = page.waitForRequest(request => request.method() === "POST");
    await page.locator('[name="phone"]').press("Enter");
    const data = new URLSearchParams((await posted).postData()!);
    expect(data.get("channel")).toBe("telegram");
    expect(data.get("next")).toBe("/app/?source=channels&nested=yes");
    expect(data.has("login")).toBe(false);
    await expect(page.locator('[data-login-panel="telegram"] [data-slot="field-error"]')).toBeVisible();
    await expect(page.getByRole("button", { name: "Телефон Telegram", exact: true })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator('[name="phone"]')).toHaveValue("invalid");
  } else {
    await expect(page.locator("[data-channel-selector]")).toHaveCount(0);
  }
  expect(await page.locator("[id]").evaluateAll(nodes => new Set(nodes.map(node => node.id)).size === nodes.length)).toBe(true);
  await page.goto("/accounts/login/");
  if (capabilities.passkeyLoginEnabled) await expect(page.locator("#passkey_login")).toBeEnabled();
  await page.screenshot({ path: testInfo.outputPath(`login-${passwordMode}-desktop.png`), fullPage: true });
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`login-${passwordMode}-${width}.png`), fullPage: true });
  }
  const noJS = await browser.newContext({ javaScriptEnabled: false });
  const fallback = await noJS.newPage();
  await fallback.goto("/accounts/login/?next=/app/?source=fallback-channel");
  if (capabilities.phoneCodeLoginEnabled) {
    await fallback.getByRole("link", { name: "Телефон Telegram", exact: true }).click();
    await expect(fallback.locator('[name="phone"]')).toBeVisible();
    await expect(fallback.locator('[name="login"]')).toBeHidden();
    await fallback.getByRole("link", { name: "Email", exact: true }).click();
    await expect(fallback.locator('[name="login"]')).toBeVisible();
    expect(new URL(fallback.url()).searchParams.get("next")).toBe("/app/?source=fallback-channel");
  }
  await noJS.close();
  expect(errors).toEqual([]);
});

test("signup fields stay compact and OTP supports errors, resend and complete paste", async ({ page }, testInfo) => {
  runFixture("reset");
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/accounts/signup/");
  await page.waitForFunction("window.coreUIState === 'ready'");
  await expect(page.locator(".auth-card-signup")).toBeVisible();
  const surname = await page.locator('[name="last_name"]').boundingBox();
  const givenName = await page.locator('[name="first_name"]').boundingBox();
  expect(Math.abs(surname!.y - givenName!.y)).toBeLessThan(1);
  expect(givenName!.x).toBeGreaterThan(surname!.x);
  await page.screenshot({ path: testInfo.outputPath(`signup-${passwordMode}-desktop.png`), fullPage: true });
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const first = await page.locator('[name="last_name"]').boundingBox();
    const second = await page.locator('[name="first_name"]').boundingBox();
    expect(second!.y).toBeGreaterThan(first!.y + first!.height);
    await page.screenshot({ path: testInfo.outputPath(`signup-${passwordMode}-${width}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/accounts/login/code/?channel=email&next=/app/?source=otp-card");
  await page.locator('[name="email"]').fill("core_e2e_qa@example.invalid");
  await page.locator('[name="email"]').press("Enter");
  await expect(page.locator(".auth-card-code")).toBeVisible();
  await page.waitForFunction("window.coreUIState === 'ready'");
  await expect(page.locator('[data-slot="input-otp-slot"]')).toHaveCount(6);
  const original = runFixture("login-mail").code as string;
  const wrong = `${(Number(original[0]) + 1) % 10}${original.slice(1)}`;
  await page.locator('input[name="code"]').fill(wrong);
  await page.locator('input[name="code"]').press("Enter");
  await expect(page.locator('[data-slot="field-error"]')).toBeVisible();
  await expect(page.locator(".auth-card-code")).toBeVisible();
  if (await page.locator("#resend").count()) {
    await page.locator("#resend button").click();
    await expect(page.locator(".auth-card-code")).toBeVisible();
  }
  const code = runFixture("login-mail").code as string;
  await page.screenshot({ path: testInfo.outputPath("otp-desktop.png"), fullPage: true });
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`otp-${width}.png`), fullPage: true });
  }
  await page.locator('input[name="code"]').fill(code);
  await expect(page.locator('[data-slot="input-otp-slot"]').first()).toHaveText(code[0]!);
  await page.locator('input[name="code"]').press("Enter");
  await expect(page).toHaveURL(/\/app\/\?source=otp-card$/);
  expect(errors).toEqual([]);
});
