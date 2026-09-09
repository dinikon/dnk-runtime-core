import { expect, test, type Page } from "@playwright/test";

const loginPath = "/accounts/login/?next=%2Fapp%2F%3Fsource%3Dwebauthn-e2e";
const passkeyPath = "/accounts/2fa/webauthn/login/";

async function assertGuest(page: Page) {
  const response = await page.request.get("/api/session/");
  expect((await response.json()).authenticated).toBe(false);
}

async function logout(page: Page) {
  await page.goto("/accounts/logout/");
  await page.locator('form[action="/accounts/logout/"] button[type="submit"]').click();
  await expect(page).toHaveURL((url) => url.pathname === "/");
  await assertGuest(page);
}

test("real passkey enrollment, UV enforcement, cancellation and recovery", async ({ page, context }, testInfo) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  const cdp = await context.newCDPSession(page);
  await cdp.send("WebAuthn.enable");
  const { authenticatorId } = await cdp.send("WebAuthn.addVirtualAuthenticator", {
    options: {
      protocol: "ctap2",
      transport: "internal",
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  });

  await test.step("password login returns to the protected Nuxt route", async () => {
    await page.goto(loginPath);
    await page.locator('[name="login"]').fill("core_e2e_qa@example.invalid");
    await page.locator('[name="password"]').fill(process.env.CORE_E2E_PASSWORD!);
    await page.locator('form[action="/accounts/login/"] button[type="submit"]').click();
    await expect(page).toHaveURL(/\/app\/\?source=webauthn-e2e$/);
    await expect(page.getByRole("heading", { name: "Core E2E Fixture" })).toBeVisible();
  });

  await test.step("enroll a resident passkey through the real allauth ceremony", async () => {
    await page.goto("/accounts/2fa/webauthn/add/");
    await page.locator('[name="name"]').fill("E2E virtual passkey");
    await expect(page.locator('[name="passwordless"]')).toBeChecked();
    await expect(page.locator('[name="passwordless"]')).toBeDisabled();
    const options = JSON.parse((await page.locator("#js_data").textContent())!);
    expect(options.creation_options.publicKey.authenticatorSelection).toMatchObject({ userVerification: "required", residentKey: "required" });
    await page.locator("#mfa_webauthn_add").click();
    await expect(page).toHaveURL(/\/accounts\/2fa\/(webauthn|recovery-codes)\/$/);
    await page.goto("/accounts/2fa/webauthn/");
    await expect(page.getByRole("cell", { name: /^E2E virtual passkey/ })).toBeVisible();
    const { credentials } = await cdp.send("WebAuthn.getCredentials", { authenticatorId });
    expect(credentials).toHaveLength(1);
    expect(credentials[0]?.isResidentCredential).toBe(true);
    await logout(page);
  });

  await test.step("cancelling a real WebAuthn request leaves the user signed out", async () => {
    await page.goto(loginPath);
    await cdp.send("WebAuthn.setAutomaticPresenceSimulation", { authenticatorId, enabled: false });
    await page.evaluate(() => {
      const original = navigator.credentials.get.bind(navigator.credentials);
      navigator.credentials.get = (options) => {
        navigator.credentials.get = original;
        const controller = new AbortController();
        const pending = original({ ...options, signal: controller.signal });
        setTimeout(() => controller.abort(), 50);
        return pending;
      };
    });
    await page.locator("#passkey_login").click();
    await expect(page.locator("#webauthn-feedback")).toContainText("отменено или не подтверждено");
    await assertGuest(page);
    await cdp.send("WebAuthn.setAutomaticPresenceSimulation", { authenticatorId, enabled: true });
  });

  await test.step("a failed challenge request can be retried without reloading", async () => {
    await page.route(`**${passkeyPath}`, (route) => route.fulfill({ status: 503, body: "temporarily unavailable" }), { times: 1 });
    await page.locator("#passkey_login").click();
    await expect(page.locator("#webauthn-feedback")).toContainText("Проверьте соединение");
    await assertGuest(page);
    await page.screenshot({ path: testInfo.outputPath("passkey-network-feedback.png") });
    await page.locator("#passkey_login").click();
    await expect(page).toHaveURL(/\/app\/\?source=webauthn-e2e$/);
    await expect(page.getByRole("heading", { name: "Core E2E Fixture" })).toBeVisible();
    await logout(page);
  });

  await test.step("an assertion with the UV bit cleared cannot establish a session", async () => {
    await page.goto(loginPath);
    await cdp.send("WebAuthn.setResponseOverrideBits", { authenticatorId, isBadUV: true });
    const posted = page.waitForResponse((response) => response.url().endsWith(passkeyPath) && response.request().method() === "POST");
    await page.locator("#passkey_login").click();
    const response = await posted;
    const credential = JSON.parse(new URLSearchParams(response.request().postData()!).get("credential")!);
    expect(Buffer.from(credential.response.authenticatorData, "base64url")[32]! & 0x04).toBe(0);
    expect(response.status()).toBe(302);
    await expect(page).toHaveURL(/\/accounts\/login\/$/);
    await expect(page.locator(".messages")).toContainText("PIN-кода или биометрии");
    await assertGuest(page);
    await cdp.send("WebAuthn.setResponseOverrideBits", { authenticatorId });
    await page.goto(loginPath);
    await page.locator("#passkey_login").click();
    await expect(page).toHaveURL(/\/app\/\?source=webauthn-e2e$/);
  });

  await test.step("Nuxt keeps the session on API failure and recovers on retry", async () => {
    await page.route("**/api/session/", (route) => route.fulfill({ status: 503, body: "temporarily unavailable" }), { times: 1 });
    await page.goto("/app/");
    await expect(page.getByRole("heading", { name: "Не удалось загрузить аккаунт" })).toBeVisible();
    await expect(page).toHaveURL(/\/app\/$/);
    await page.getByRole("button", { name: "Попробовать снова" }).click();
    await expect(page.getByRole("heading", { name: "Core E2E Fixture" })).toBeVisible();
  });

  await test.step("the public Hero offers a quiet retry on session lookup failure", async () => {
    await page.route("**/api/session/", (route) => route.fulfill({ status: 503, body: "temporarily unavailable" }), { times: 1 });
    await page.goto("/");
    await expect(page.getByRole("status")).toContainText("Не удалось проверить аккаунт");
    await page.getByRole("button", { name: "Повторить" }).click();
    await expect(page.getByRole("link", { name: "Открыть приложение" })).toBeVisible();
  });

  expect(browserErrors).toEqual([]);
  await cdp.send("WebAuthn.removeVirtualAuthenticator", { authenticatorId });
});
