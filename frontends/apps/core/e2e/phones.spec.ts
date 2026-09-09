import { expect, test, type Page } from "@playwright/test";
import { runFixture } from "./fixture";

const first = "+12025550123";
const second = "+12025550124";

async function login(page: Page) {
  await page.goto("/accounts/login/?next=/accounts/phone/change/");
  const capabilities = await (await page.request.get("/api/capabilities/")).json();
  await page.locator('[name="login"]').fill("core_e2e_qa@example.invalid");
  if (capabilities.passwordLoginEnabled) {
    await page.locator('[name="password"]').fill(process.env.CORE_E2E_PASSWORD!);
    await page.locator('[name="password"]').press("Enter");
  } else {
    await page.locator('[name="login"]').press("Enter");
    await expect(page.locator('[name="code"]')).toBeVisible();
    await page.locator('[name="code"]').fill(runFixture("login-mail").code as string);
    await page.locator('[name="code"]').press("Enter");
  }
  await expect(page).toHaveURL(/\/accounts\/phone\/change\/$/);
}

async function confirmPhone(page: Page) {
  await expect(page).toHaveURL(/\/accounts\/phone\/verify\/$/);
  await page.locator('[name="code"]').fill(runFixture("phone-code").code as string);
  await page.locator('[name="code"]').press("Enter");
  await expect(page).toHaveURL(/\/accounts\/phone\/change\/$/);
}

test("phone enrollment, primary selection and removal work on desktop, mobile and without JS", async ({ page, browser }, testInfo) => {
  runFixture("reset");
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await login(page);
  await expect(page).toHaveTitle(/Телефоны/);
  await expect(page.getByRole("heading", { name: "Телефоны", exact: true })).toBeVisible();
  await page.waitForFunction("window.coreUIState === 'ready'");
  await page.getByLabel("Номер телефона", { exact: true }).fill(first);
  await page.getByLabel("Номер телефона", { exact: true }).press("Enter");
  await expect(page).toHaveURL(/\/accounts\/phone\/verify\/$/);
  const valid = runFixture("phone-code").code as string;
  await page.locator('[name="code"]').fill(valid === "000000" ? "111111" : "000000");
  await page.locator('[name="code"]').press("Enter");
  await expect(page.getByText("Неверный код.", { exact: true })).toBeVisible();
  await page.waitForFunction("window.coreUIState === 'ready'");
  // Use a real clipboard paste; synthetic ClipboardEvents do not perform native insertion.
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.evaluate((code) => navigator.clipboard.writeText(code), valid);
  await page.locator('[name="code"]').press("ControlOrMeta+A");
  await page.locator('[name="code"]').press("ControlOrMeta+V");
  await expect(page.locator('[name="code"]')).toHaveValue(valid);
  await page.screenshot({ path: testInfo.outputPath("phone-otp.png"), fullPage: true });
  await page.locator('[name="code"]').press("Enter");
  await expect(page).toHaveURL(/\/accounts\/phone\/change\/$/);
  const firstRow = page.locator(".phone-row").filter({ has: page.getByRole("heading", { name: first, exact: true }) });
  await expect(firstRow.getByText("Основной", { exact: true })).toBeVisible();

  await page.getByLabel("Номер телефона", { exact: true }).fill(second);
  await page.getByRole("button", { name: "Получить код в Telegram", exact: true }).click();
  await confirmPhone(page);
  const secondRow = page.locator(".phone-row").filter({ has: page.getByRole("heading", { name: second, exact: true }) });
  await expect(firstRow.getByRole("button", { name: "Удалить", exact: true })).toBeDisabled();
  await secondRow.getByRole("button", { name: "Сделать основным", exact: true }).click();
  await expect(secondRow.getByText("Основной", { exact: true })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("phones-desktop.png"), fullPage: true });
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`phones-${width}.png`), fullPage: true });
  }
  await page.goto("/accounts/");
  await expect(page.getByText(`${second} · Основной`, { exact: true })).toBeVisible();
  await expect(page.getByText("Дополнительных номеров: 1", { exact: true })).toBeVisible();

  const noJS = await browser.newContext({ javaScriptEnabled: false, storageState: await page.context().storageState() });
  const fallback = await noJS.newPage();
  await fallback.goto("/accounts/phone/change/");
  const fallbackFirst = fallback.locator(".phone-row").filter({ has: fallback.getByRole("heading", { name: first, exact: true }) });
  await fallbackFirst.getByRole("button", { name: "Сделать основным", exact: true }).click();
  const fallbackSecond = fallback.locator(".phone-row").filter({ has: fallback.getByRole("heading", { name: second, exact: true }) });
  await fallbackSecond.getByRole("button", { name: "Удалить", exact: true }).click();
  await expect(fallbackSecond).toHaveCount(0);
  await fallback.locator('[name="phone"]').fill(second);
  await fallback.getByRole("button", { name: "Получить код в Telegram", exact: true }).click();
  await confirmPhone(fallback);
  await expect(fallbackSecond.getByText("Подтверждён", { exact: true })).toBeVisible();
  for (const width of [360, 390]) {
    await fallback.setViewportSize({ width, height: 844 });
    expect(await fallback.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await fallback.screenshot({ path: testInfo.outputPath(`phones-nojs-${width}.png`), fullPage: true });
  }
  await noJS.close();
  expect(errors).toEqual([]);
});

test("phone login follows the actual server mode and preserves the primary contact", async ({ page, browser }) => {
  runFixture("reset");
  await login(page);
  for (const number of [first, second]) {
    await page.locator('[name="phone"]').fill(number);
    await page.getByRole("button", { name: "Получить код в Telegram", exact: true }).click();
    await confirmPhone(page);
  }
  const capabilities = await (await page.request.get("/api/capabilities/")).json();
  expect(capabilities.phoneLoginMode).toBe(process.env.CORE_E2E_AUTH_PHONE_LOGIN_MODE ?? "any_verified");
  const context = await browser.newContext();
  const guest = await context.newPage();
  const number = capabilities.phoneLoginMode === "primary_only" ? first : second;
  await guest.goto("/accounts/login/code/?channel=telegram&next=/app/?phone=yes");
  await guest.locator('[name="phone"]').fill(number);
  await guest.locator('[name="phone"]').press("Enter");
  await expect(guest.locator('[name="code"]')).toBeVisible();
  const delivery = runFixture("phone-code");
  expect(delivery.phone).toBe(number);
  await guest.locator('[name="code"]').fill(delivery.code as string);
  await guest.locator('[name="code"]').press("Enter");
  await expect(guest).toHaveURL(/\/app\/\?phone=yes$/);
  const phones = runFixture("phones").phones as Array<{ phone: string; primary: boolean }>;
  expect(phones.find((phone) => phone.primary)?.phone).toBe(first);
  await context.close();
});
