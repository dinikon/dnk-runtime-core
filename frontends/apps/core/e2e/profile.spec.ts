import { expect, test } from "@playwright/test";
import { runFixture } from "./fixture";

test("names can be edited with and without JavaScript and appear throughout the account", async ({ page, browser }, testInfo) => {
  runFixture("reset");
  const capabilities = await (await page.request.get("/api/capabilities/")).json();
  await page.goto("/accounts/login/?next=/accounts/profile/");
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
  await expect(page).toHaveURL(/\/accounts\/profile\/$/);
  await page.waitForFunction("window.coreUIState === 'ready'");
  await expect(page.locator('[name="username"]')).toHaveCount(0);
  await expect(page.locator('[name="first_name"]')).toHaveValue("Core E2E Fixture");
  await page.getByLabel("Фамилия", { exact: true }).fill("Перевірка");
  await page.getByLabel("Отчество", { exact: true }).fill("Тест");
  await page.locator('[name="middle_name"]').press("Enter");
  await expect(page.getByText("Данные профиля сохранены.")).toBeVisible();
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: testInfo.outputPath(`profile-${width}.png`), fullPage: true });
  }
  await page.goto("/app/");
  await expect(page.getByRole("heading", { name: "Перевірка Core E2E Fixture Тест", exact: true })).toBeVisible();
  await expect(page.getByText("Имя пользователя", { exact: true })).toHaveCount(0);
  await page.getByRole("link", { name: "Редактировать профиль", exact: true }).click();
  await expect(page).toHaveURL(/\/accounts\/profile\/$/);

  const noJS = await browser.newContext({ javaScriptEnabled: false, storageState: await page.context().storageState() });
  const fallback = await noJS.newPage();
  await fallback.goto("/accounts/profile/");
  await fallback.getByLabel(/^Фамилия:?$/).fill("Оновлена");
  await fallback.getByLabel(/^Отчество:?$/).fill("");
  await fallback.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(fallback.getByText("Данные профиля сохранены.")).toBeVisible();
  await fallback.goto("/accounts/");
  await expect(fallback.locator(".settings-profile strong")).toHaveText("Оновлена Core E2E Fixture");
  const profile = await (await fallback.request.get("/api/me/")).json();
  expect(profile.username).toBe("core_e2e_qa");
  expect(profile.middle_name).toBe("");
  await noJS.close();
});
