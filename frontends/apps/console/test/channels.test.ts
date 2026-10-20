import { normalizeApiError } from "../src/modules/channels/api/channels.error.ts";
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mapPublication,
  mapConnection,
  mapPlatform,
  updateConnectionPayload,
} from "../src/modules/channels/api/channels.mapper.ts";
import {
  initializationLabel,
  initializationActive,
  platformSupported,
  decimalLabel,
} from "../src/modules/channels/model/channels.presentation.ts";
import {
  connectionFormValues,
  connectionSettings,
  validateConnectionForm,
} from "../src/modules/channels/model/connection-form.ts";
import {
  parsePage,
  parseStockStatus,
} from "../src/modules/channels/model/channels.url-state.ts";
import type {
  Platform,
  Initialization,
} from "../src/modules/channels/model/channels.types.ts";
const platform: Platform = {
  kind: "new-plugin",
  label: "New plugin",
  sdkVersion: 5,
  configVersion: 3,
  settingsSchema: {
    type: "object",
    additionalProperties: false,
    required: ["locales", "currency"],
    properties: {
      locales: {
        type: "array",
        minItems: 1,
        maxItems: 2,
        uniqueItems: true,
        items: { type: "string", "x-reference": "locale" },
      },
      currency: {
        type: "string",
        minLength: 3,
        maxLength: 3,
        "x-reference": "currency",
      },
    },
  },
  capabilities: ["verify_connection", "read_publications"],
  endpointSchema: {
    type: "string",
    const: "https://api.example",
    default: "https://api.example",
  },
  credentialsSchema: {
    type: "object",
    properties: { api_key: { type: "string", writeOnly: true } },
    required: ["api_key"],
  },
};
const run: Initialization = {
  runId: "run",
  connectionId: "connection",
  status: "partial",
  processed: 3,
  invalid: 0,
  sequence: 2,
  reasonCode: "scope_limited",
  scopeLimitations: ["api_visible_statuses_only"],
  updatedAt: null,
  jobId: null,
  readComplete: true,
  recoveryRequired: false,
};
test("completed partial scope differs from interrupted and requires no spinner", () => {
  assert.match(initializationLabel(run), /завершена с ограничениями/);
  assert.match(
    initializationLabel({ ...run, readComplete: false }),
    /прервана/,
  );
  assert.equal(initializationActive(run), false);
  assert.equal(initializationActive({ ...run, status: "running" }), true);
  assert.equal(
    initializationActive({ ...run, status: "running", recoveryRequired: true }),
    false,
  );
  assert.match(
    initializationLabel({ ...run, recoveryRequired: true }),
    /восстановления/,
  );
});
test("a new plugin config supplies fixed endpoint and fields without kind conditions", () => {
  const values = connectionFormValues(platform, undefined);
  assert.equal(values.endpoint, "https://api.example");
  assert.deepEqual(values.credentials, { api_key: "" });
  assert.equal(platformSupported(platform), true);
  assert.equal(platformSupported({ ...platform, sdkVersion: 1 }), false);
  assert.equal(
    platformSupported({
      ...platform,
      credentialsSchema: {
        type: "object",
        properties: { nested: { type: "object" } },
      },
    }),
    false,
  );
  values.settings = { locales: ["uk", "ru"], currency: "UAH" };
  assert.match(
    validateConnectionForm(values, platform, true) ?? "",
    /поля доступа/,
  );
  values.credentials.api_key = "secret";
  assert.equal(validateConnectionForm(values, platform, true), null);
  values.settings.locales = ["uk", "uk"];
  assert.match(
    validateConnectionForm(values, platform, true) ?? "",
    /должны отличаться/,
  );
});
test("settings and credential replacement are explicit; unchanged secrets are omitted", () => {
  const values = connectionFormValues(platform, undefined);
  values.settings = { locales: ["uk"], currency: "UAH" };
  assert.deepEqual(connectionSettings(values), {
    endpoint: "https://api.example",
    options: { locales: ["uk"], currency: "UAH" },
  });
  const input = {
    channelId: "id",
    revision: 4,
    settings: connectionSettings(values),
  };
  assert.equal(
    Object.hasOwn(updateConnectionPayload(input), "credentials"),
    false,
  );
  assert.deepEqual(
    updateConnectionPayload({ ...input, credentials: { api_key: "new" } })
      .credentials,
    { api_key: "new" },
  );
});
test("publication mapper preserves exact decimal strings, zero and unknown values", () => {
  const item = mapPublication({
    publication_id: "p",
    connection_id: "c",
    resource_type: "product",
    external_id: "native",
    external_sku: null,
    price: "9007199254740993.000001",
    sale_price: "0",
    currency: "UAH",
    quantity: null,
    stock_status: "unknown",
    title: null,
    title_locale: null,
    main_image_url: null,
    source_updated_at: null,
    warnings: ["quantity_not_exposed"],
    observed_revision: 1,
    first_seen_at: "2026-10-18T00:00:00Z",
    last_seen_at: "2026-10-18T00:00:00Z",
    last_import_run_id: "r",
  });
  assert.equal(item.price, "9007199254740993.000001");
  assert.equal(decimalLabel(item.salePrice, item.currency), "0 UAH");
  assert.equal(decimalLabel(item.quantity), "—");
  assert.equal(item.externalSku, null);
});
test("connection mapping exposes presence flags, never invents credential values", () => {
  const connection = mapConnection({
    channel_id: "ch",
    connection_id: "co",
    revision: 2,
    endpoint: "https://api.example",
    settings: { locales: ["uk", "ru"], currency: "UAH" },
    resource_identity: null,
    verification_status: "queued",
    verification_job_id: "job",
    generation: 1,
    is_paused: false,
    credentials_present: false,
    candidate_present: true,
    reason_code: null,
    scope_limitations: [],
  });
  assert.equal(connection.candidatePresent, true);
  assert.equal(Object.hasOwn(connection, "credentials"), false);
});
test("URL state normalizes invalid pagination and unsupported stock filters", () => {
  for (const input of [
    undefined,
    "0",
    "-1",
    "Infinity",
    "1e3",
    "9999999999999999999",
    ["2"],
  ])
    assert.equal(parsePage(input), 1);
  assert.equal(parsePage("12"), 12);
  assert.equal(parseStockStatus("unknown"), "unknown");
  assert.equal(parseStockStatus("invented"), "");
});

test("Decimal exponent display preserves exact value without binary floating point", () => {
  assert.equal(decimalLabel("0E-12"), "0");
  assert.equal(decimalLabel("100.000000000000", "UAH"), "100 UAH");
  assert.equal(decimalLabel("1.250000000000"), "1.25");
  assert.equal(
    decimalLabel("1.234567890123456789E-3"),
    "0.001234567890123456789",
  );
  assert.equal(
    decimalLabel("9007199254740993.000001"),
    "9007199254740993.000001",
  );
});

test("form validation rejects unsafe endpoint syntax and allows unchanged credentials", () => {
  const configurable = { ...platform, endpointSchema: { type: "string" } };
  const values = connectionFormValues(configurable, undefined);
  values.settings = { locales: ["uk"], currency: "UAH" };
  for (const endpoint of [
    "http://shop.example",
    "https://u:p@shop.example",
    "https://shop.example/?token=x",
    "https://shop.example/#secret",
    "https://shop.example:8080",
  ]) {
    values.endpoint = endpoint;
    assert.ok(validateConnectionForm(values, configurable, false));
  }
  values.endpoint = "https://shop.example";
  assert.equal(validateConnectionForm(values, configurable, false), null);
});

test("transport errors cannot retain credentials in UI or mutation errors", () => {
  const raw = Object.assign(new Error("private-token"), {
    isAxiosError: true,
    config: { data: { credentials: { token: "private-token" } } },
    response: { status: 422, data: { detail: [{ input: "private-token" }] } },
  });
  const safe = normalizeApiError(raw);
  assert.equal(safe.code, "request_failed");
  assert.equal(safe.status, 422);
  assert.equal(Object.hasOwn(safe, "config"), false);
  assert.doesNotMatch(safe.stack ?? "", /private-token/);
  assert.doesNotMatch(JSON.stringify(safe), /private-token/);
});

test("missing or unsupported plugin settings schema fails closed", () => {
  assert.equal(platformSupported(platform), true);
  for (const sdkVersion of [1, 2, 3, 4]) {
    assert.equal(platformSupported({ ...platform, sdkVersion }), false);
  }
  assert.equal(platformSupported({ ...platform, configVersion: 2 }), false);
  assert.equal(
    platformSupported({
      ...platform,
      settingsSchema: undefined,
    } as unknown as Platform),
    false,
  );
  assert.equal(
    platformSupported({
      ...platform,
      settingsSchema: {
        type: "object",
        properties: { unknown: { type: "unsupported" } },
      },
    }),
    false,
  );
  assert.equal(
    platformSupported({
      ...platform,
      settingsSchema: { type: "object", anyOf: [] },
    } as unknown as Platform),
    false,
  );
});

test("manifest settings schema supplies fixed values and validates optional array slots", () => {
  const fixed = mapPlatform({
    kind: "fixed-plugin",
    label: "Fixed",
    sdk_version: 5,
    config_version: 3,
    capabilities: platform.capabilities,
    credentials_schema: platform.credentialsSchema,
    endpoint_schema: platform.endpointSchema,
    settings_schema: {
      type: "object",
      additionalProperties: false,
      required: ["locales", "currency"],
      properties: {
        locales: {
          type: "array",
          minItems: 1,
          maxItems: 2,
          uniqueItems: true,
          default: ["ru"],
          items: { type: "string", enum: ["ru", "uk"] },
          prefixItems: [
            { type: "string", const: "ru", title: "Основной язык" },
            { type: "string", enum: ["uk"], title: "Дополнительный язык" },
          ],
        },
        currency: { type: "string", const: "UAH", default: "UAH" },
      },
    },
  });
  assert.equal(platformSupported(fixed), true);
  const values = connectionFormValues(fixed, undefined);
  values.credentials.api_key = "secret";
  assert.deepEqual(values.settings, { locales: ["ru"], currency: "UAH" });
  assert.equal(validateConnectionForm(values, fixed, true), null);
  values.settings.locales = ["ru", "uk"];
  assert.equal(validateConnectionForm(values, fixed, true), null);
  values.settings.locales = ["ru", "en"];
  assert.ok(validateConnectionForm(values, fixed, true));
  values.settings.locales = ["uk"];
  assert.match(
    validateConnectionForm(values, fixed, true) ?? "",
    /фиксированное/,
  );
  values.settings.locales = ["ru"];
  values.settings.currency = "USD";
  assert.match(
    validateConnectionForm(values, fixed, true) ?? "",
    /фиксированное/,
  );
});

test("new plugin fields, nested objects, booleans and numbers need no platform conditions", () => {
  const extra: Platform = {
    ...platform,
    settingsSchema: {
      type: "object",
      additionalProperties: false,
      required: ["limit", "advanced"],
      properties: {
        limit: { type: "integer", minimum: 1, maximum: 1000, default: 50 },
        advanced: {
          type: "object",
          additionalProperties: false,
          required: ["enabled"],
          properties: { enabled: { type: "boolean", default: false } },
        },
      },
    },
  };
  const values = connectionFormValues(extra, undefined);
  assert.equal(platformSupported(extra), true);
  assert.deepEqual(values.settings, {
    limit: 50,
    advanced: { enabled: false },
  });
  assert.equal(validateConnectionForm(values, extra, false), null);
  values.settings.limit = 0;
  assert.ok(validateConnectionForm(values, extra, false));
  values.settings.limit = 5;
  values.settings.unknown = "extra";
  assert.ok(validateConnectionForm(values, extra, false));
});
