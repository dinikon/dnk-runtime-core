/** Contract-backed browser regression. Requires Console on CURRENCY_UI_URL and Playwright. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const browser = await chromium.launch({ headless: true });
const base = process.env.CURRENCY_UI_URL || "http://127.0.0.1:5179";
const directory = [
  { code: "UAH", name: "Hryvnia", minor_units: 2 },
  { code: "USD", name: "US Dollar", minor_units: 2 },
  { code: "EUR", name: "Euro", minor_units: 2 },
  { code: "JPY", name: "Yen", minor_units: 0 },
];
const defaultPolicy = {
  default_transaction_currency: "UAH",
  provider_code: "NBU",
  rate_date_policy: "previous_available",
  rounding_mode: "ROUND_HALF_UP",
  allow_cross_rate: true,
  bridge_currency: "UAH",
  business_timezone: "Europe/Kyiv",
  version: 1,
  default_display_currency: null,
};
const permissions = [
  "currency.view",
  "currency.manage_policy",
  "currency.manage_rates",
  "currency.manage_enabled",
  "currency.change_functional_currency",
];
async function fixture({
  configured = true,
  member = false,
  preference = null,
} = {}) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => {
    errors.push(error.message);
    process.stderr.write(error.message + "\n");
  });
  const state = {
    configured,
    policy: configured ? { ...defaultPolicy } : null,
    preference,
    conflict: false,
    writes: [],
    rateRows: [],
    extraPeriods: [],
  };
  const settings = () => ({
    configured: state.configured,
    policy: state.policy,
    enabled_currencies: state.configured ? ["UAH", "USD", "EUR"] : [],
    functional_currency: state.configured ? "UAH" : null,
    future_functional_currency: null,
    default_display_currency:
      state.policy?.default_display_currency ||
      (state.configured ? "UAH" : null),
    business_date: "2026-09-21",
    next_business_day_at: "2099-09-22T00:00:00Z",
    periods: state.configured
      ? [
          {
            id: "period",
            currency: "UAH",
            valid_from: "2020-01-01",
            valid_to: null,
            reason: "Первый период",
          },
          ...state.extraPeriods,
        ]
      : [],
    permissions: member ? ["currency.view"] : permissions,
    provider_status: { last_import: null, last_available_rate_date: null },
  });
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const method = req.method();
    if (!path.startsWith("/api/")) return route.continue();
    let body;
    let status = 200;
    if (path.endsWith("/auth/csrf")) body = { csrf_token: "browser-test-csrf" };
    else if (path.endsWith("/auth/me/display-currency")) {
      assert.equal(req.headers()["x-csrf-token"], "browser-test-csrf");
      state.preference = req.postDataJSON().display_currency;
      state.writes.push(req.postDataJSON());
      body = { display_currency: state.preference };
    } else if (path.endsWith("/auth/me"))
      body = {
        id: "user",
        role: member ? "member" : "admin",
        status: "active",
        first_name: "Currency",
        last_name: "Tester",
        middle_name: null,
        avatar: null,
        interface_language: "ru",
        interface_theme: "light",
        timezone: "Europe/Kyiv",
        display_currency: state.preference,
        emails: [],
      };
    else if (path.includes("resolve"))
      body = {
        exists: true,
        available: true,
        status: "active",
        tenant_id: "tenant",
        tenant_name: "Currency test",
        api_host: null,
      };
    else if (path.endsWith("/currency/settings")) body = settings();
    else if (path.endsWith("/currency/directory")) body = directory;
    else if (path.endsWith("/currency/sources"))
      body = ["MANUAL", "NBU"].map((code) => ({
        code,
        local: code === "MANUAL",
        capabilities: {
          historical_rates: true,
          supported_currencies: false,
          base_currency: null,
          bulk_download: code === "NBU",
        },
      }));
    else if (path.endsWith("/currency/rates")) body = state.rateRows;
    else if (path.endsWith("/currency/rates/manual")) {
      const input = req.postDataJSON();
      state.writes.push(input);
      state.rateRows = state.rateRows.map((row) => ({
        ...row,
        is_current: false,
      }));
      body = {
        id: "new-rate",
        pair: { source: input.source_currency, target: input.target_currency },
        rate: input.rate,
        effective_date: input.effective_date,
        provider_code: "MANUAL",
        revision: 3,
        is_current: true,
      };
      state.rateRows.unshift(body);
      status = 201;
    } else if (path.endsWith("/currency/periods") && method === "POST") {
      const input = req.postDataJSON();
      state.writes.push(input);
      body = {
        id: "future-period",
        currency: input.currency,
        valid_from: input.effective_from,
        valid_to: null,
        reason: input.reason,
      };
      state.extraPeriods.push(body);
      status = 201;
    } else if (path.endsWith("/currency/initialize")) {
      assert.equal(req.headers()["x-csrf-token"], "browser-test-csrf");
      const input = req.postDataJSON();
      state.writes.push(input);
      assert.equal(input.business_timezone, "Europe/Kyiv");
      state.configured = true;
      state.policy = { ...defaultPolicy };
      body = { ok: true };
      status = 201;
    } else if (path.endsWith("/currency/policy") && method === "PUT") {
      const input = req.postDataJSON();
      state.writes.push(input);
      if (state.conflict) {
        status = 409;
        body = { detail: { code: "currency_conflict", message: "Reload" } };
      } else {
        state.policy = { ...input, version: input.expected_version + 1 };
        body = state.policy;
      }
    } else {
      body = [];
    }
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
  return { context, page, state, errors };
}
async function check(name, fn) {
  try {
    await fn();
    process.stdout.write(`PASS ${name}\n`);
  } catch (error) {
    process.stderr.write(`FAIL ${name}\n`);
    for (const context of browser.contexts())
      for (const page of context.pages()) {
        await page.screenshot({
          path: "/tmp/currency-browser-failure.png",
          fullPage: true,
        });
        process.stderr.write((await page.locator("body").innerText()) + "\n");
      }
    throw error;
  }
}
try {
  await check(
    "explicit initialization, defaults, and historical periods",
    async () => {
      const { context, page, state, errors } = await fixture({
        configured: false,
      });
      await page.goto(`${base}/settings/currency`);
      await page
        .getByText("Валютная политика ещё не настроена", { exact: true })
        .waitFor();
      assert.equal(state.writes.length, 0);
      await page
        .getByRole("button", { name: "Настроить валюты", exact: true })
        .click();
      await page
        .getByRole("button", { name: "Сохранить политику", exact: true })
        .waitFor();
      assert.equal(state.writes.length, 1);
      assert.equal(state.writes[0].default_display_currency, null);
      await page.getByRole("tab", { name: "История основной валюты" }).click();
      await page.getByText("Первый период", { exact: true }).waitFor();
      await page.screenshot({
        path:
          process.env.CURRENCY_SCREENSHOT ||
          "/tmp/currency-console-history.png",
        fullPage: true,
      });
      assert.deepEqual(errors, []);
      await context.close();
    },
  );
  await check(
    "409 preserves draft and requires deliberate reload",
    async () => {
      const { context, page, state, errors } = await fixture();
      state.conflict = true;
      await page.goto(`${base}/settings/currency`);
      await page.getByLabel("Часовой пояс организации").fill("Europe/Warsaw");
      await page
        .getByRole("button", { name: "Сохранить политику", exact: true })
        .click();
      await page
        .getByRole("button", { name: "Загрузить актуальные данные" })
        .waitFor();
      assert.equal(
        await page.getByLabel("Часовой пояс организации").inputValue(),
        "Europe/Warsaw",
      );
      assert.equal(
        await page
          .getByRole("button", { name: "Сохранить политику", exact: true })
          .isDisabled(),
        true,
      );
      await page
        .getByRole("button", { name: "Загрузить актуальные данные" })
        .click();
      await page.waitForFunction(
        () =>
          document.querySelector("#business-timezone")?.value === "Europe/Kyiv",
      );
      assert.deepEqual(errors, []);
      await context.close();
    },
  );
  await check(
    "member reads settings, empty rates, and cannot edit policy",
    async () => {
      const { context, page, state, errors } = await fixture({ member: true });
      await page.goto(`${base}/settings/currency`);
      await page.getByLabel("Часовой пояс организации").waitFor();
      assert.equal(
        await page.getByLabel("Часовой пояс организации").isDisabled(),
        true,
      );
      await page.getByRole("tab", { name: "Курсы", exact: true }).click();
      await page
        .getByText("Курсы пока не загружены.", { exact: false })
        .waitFor();
      assert.equal(state.writes.length, 0);
      assert.deepEqual(errors, []);
      await context.close();
    },
  );
  await check(
    "profile inheritance, personal choice, and disabled preference",
    async () => {
      const { context, page, state, errors } = await fixture({
        member: true,
        preference: "JPY",
      });
      await page.goto(`${base}/settings/account`);
      await page
        .getByText("Выбранная валюта отключена.", { exact: false })
        .waitFor();
      const select = page.getByLabel("Валюта отображения");
      assert.match(
        await select.textContent(),
        /По умолчанию организации — UAH/,
      );
      await select.selectOption("EUR");
      await page
        .getByRole("button", { name: "Сохранить валюту", exact: true })
        .click();
      await page
        .getByText("Валюта отображения сохранена.", { exact: true })
        .waitFor();
      assert.equal(state.preference, "EUR");
      await select.selectOption("inherit");
      const response = page.waitForResponse(
        (r) =>
          r.url().endsWith("/auth/me/display-currency") &&
          r.request().method() === "PUT",
      );
      await page
        .getByRole("button", { name: "Сохранить валюту", exact: true })
        .click();
      await response;
      assert.equal(state.preference, null);
      assert.deepEqual(errors, []);
      await context.close();
    },
  );
  await check(
    "manual revisions, future period and exact decimal formatting",
    async () => {
      const { context, page, state, errors } = await fixture();
      state.rateRows = [
        {
          id: "current",
          pair: { source: "USD", target: "UAH" },
          rate: "40.0001",
          effective_date: "2026-09-21",
          provider_code: "MANUAL",
          revision: 2,
          is_current: true,
        },
        {
          id: "old",
          pair: { source: "USD", target: "UAH" },
          rate: "39.9999",
          effective_date: "2026-09-21",
          provider_code: "MANUAL",
          revision: 1,
          is_current: false,
        },
      ];
      await page.goto(`${base}/settings/currency`);
      await page.getByRole("tab", { name: "Курсы", exact: true }).click();
      await page.getByText("Исторический", { exact: true }).waitFor();
      await page.getByLabel("Курс", { exact: true }).fill("41.0001");
      await page
        .getByRole("button", { name: "Сохранить курс", exact: true })
        .click();
      await page.getByText("41.0001", { exact: true }).waitFor();
      assert.equal(state.writes[0].rate, "41.0001");
      await page.getByRole("tab", { name: "История основной валюты" }).click();
      await page.getByLabel("Дата начала", { exact: true }).fill("2027-01-01");
      await page
        .getByLabel("Причина", { exact: true })
        .fill("Смена учётной валюты");
      await page
        .getByRole("button", {
          name: "Запланировать смену валюты",
          exact: true,
        })
        .click();
      await page.getByText("Смена учётной валюты", { exact: true }).waitFor();
      const formatted = await page.evaluate(async () => {
        const { formatDecimal } =
          await import("/src/modules/currency/model/format-money.ts");
        return [
          formatDecimal("9007199254740993.1234"),
          formatDecimal("1.555", 3),
          formatDecimal("2.5", 0, "ROUND_HALF_EVEN"),
          formatDecimal("1.555", 2, "ROUND_HALF_UP"),
        ];
      });
      assert.deepEqual(formatted, [
        "9\u00a0007\u00a0199\u00a0254\u00a0740\u00a0993,1234",
        "1,555",
        "2",
        "1,56",
      ]);
      assert.deepEqual(errors, []);
      await context.close();
    },
  );
} finally {
  await browser.close();
}
