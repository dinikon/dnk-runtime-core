import { test } from "node:test";
import assert from "node:assert/strict";
import {
  draftFor,
  saveDraft,
  schemaFields,
  shouldPoll,
} from "../src/modules/channels/model/channel.schema.ts";
import {
  createPayload,
  updatePayload,
  mapChannel,
} from "../src/modules/channels/api/channel.mapper.ts";
import type {
  Platform,
  Channel,
} from "../src/modules/channels/model/channel.types.ts";
const platform: Platform = {
  kind: "rozetka",
  title: "Rozetka",
  configVersion: 1,
  supportedCapabilities: ["verify_connection"],
  configSchema: {
    properties: {
      version: { const: 1 },
      endpoint: { const: "https://api-seller.rozetka.com.ua" },
      settings: { $ref: "#/$defs/Settings" },
    },
    $defs: {
      Settings: {
        properties: {
          currency: { const: "UAH", default: "UAH", title: "Валюта" },
          locales: {
            type: "array",
            default: ["ru", "uk"],
            readOnly: true,
            title: "Языки контента",
            description: "Русский — основной, Українська — дополнительный.",
          },
        },
        additionalProperties: false,
      },
    },
  },
  credentialsSchema: {
    properties: {
      token: { type: "string", format: "password", writeOnly: true },
    },
    required: ["token"],
  },
};
test("Forms resolve platform-owned nested schemas and password metadata", () => {
  const fields = schemaFields(platform.configSchema, "settings");
  assert.equal(fields.length, 2);
  assert.equal(fields[0]?.readOnly, true);
  assert.equal(fields[1]?.readOnly, true);
  assert.deepEqual(fields[1]?.defaultValue, ["ru", "uk"]);
  assert.equal(
    fields[1]?.description,
    "Русский — основной, Українська — дополнительный.",
  );
  assert.equal(schemaFields(platform.credentialsSchema)[0]?.secret, true);
  assert.equal(schemaFields(platform.configSchema)[0]?.readOnly, true);
});
test("Create serializes a complete independent secret snapshot; editing omits retained credentials", () => {
  const draft = draftFor(platform);
  draft.name = "Store";
  draft.credentials.token = "one-time-secret";
  const value = saveDraft(draft, platform);
  draft.credentials.token = "later-input";
  const body = createPayload(value);
  assert.equal(body.credentials.token, "one-time-secret");
  assert.equal(body.platform_kind, "rozetka");
  draft.replaceCredentials = false;
  assert.equal(
    "credentials" in updatePayload(saveDraft(draft, platform), 9),
    false,
  );
});
test("Reading configuration never populates secret fields; interrupted jobs stop polling", () => {
  const channel = mapChannel({
    id: "channel",
    name: "Store",
    platform_kind: "rozetka",
    revision: 3,
    config: {
      version: 1,
      endpoint: "https://api-seller.rozetka.com.ua",
      settings: {},
    },
    config_revision: 2,
    identity: null,
    verification: {
      job_id: "job",
      config_revision: 2,
      status: "pending",
      checked_at: null,
      error_code: null,
    },
    created_at: "2026-10-25",
    updated_at: "2026-10-25",
    available_capabilities: ["verify_connection"],
    recovery_required: false,
  });
  const draft = draftFor(platform, channel);
  assert.deepEqual(draft.credentials, { token: "" });
  assert.equal(draft.replaceCredentials, false);
  const saved = updatePayload(saveDraft(draft, platform), channel.revision);
  assert.deepEqual(saved.config.settings, {
    currency: "UAH",
    locales: ["ru", "uk"],
  });
  assert.deepEqual(channel.config.settings, {});
  assert.equal(shouldPoll(channel), true);
  assert.equal(shouldPoll({ ...channel, recoveryRequired: true }), false);
  assert.equal(
    shouldPoll({
      ...channel,
      verification: { ...channel.verification, status: "verified" },
    }),
    false,
  );
  assert.equal("credentials" in (channel as Channel), false);
});

const woo: Platform = {
  ...platform,
  kind: "woocommerce",
  title: "WooCommerce",
  configSchema: {
    properties: {
      endpoint: { type: "string" },
      settings: { $ref: "#/$defs/WooCommerceSettings" },
    },
    $defs: {
      WooCommerceSettings: {
        properties: {
          currency: {
            enum: ["UAH", "EUR", "USD"],
            default: "UAH",
            title: "Валюта",
          },
          locale: {
            enum: ["uk", "ru", "en"],
            default: "uk",
            title: "Язык контента",
          },
        },
      },
    },
  },
};
test("Woo uses independent scalar choices; platform defaults replace previous settings", () => {
  const fixed = draftFor(platform);
  assert.deepEqual(fixed.settings, { currency: "UAH", locales: ["ru", "uk"] });
  const selected = draftFor(woo);
  assert.deepEqual(selected.settings, { currency: "UAH", locale: "uk" });
  const fields = schemaFields(woo.configSchema, "settings");
  assert.deepEqual(
    fields.map((field) => field.options),
    [
      ["UAH", "EUR", "USD"],
      ["uk", "ru", "en"],
    ],
  );
  assert.ok(fields.every((field) => !field.readOnly));
  selected.settings.currency = "EUR";
  selected.settings.locale = "en";
  const value = saveDraft(selected, woo);
  selected.settings.locale = "ru";
  assert.deepEqual(value.config.settings, { currency: "EUR", locale: "en" });
});
test("Fixed locales remain an array and saved settings are isolated from drafts", () => {
  const first = draftFor(platform),
    second = draftFor(platform);
  const value = saveDraft(first, platform);
  (first.settings.locales as string[]).push("en");
  assert.deepEqual(value.config.settings.locales, ["ru", "uk"]);
  assert.deepEqual(second.settings.locales, ["ru", "uk"]);
});
