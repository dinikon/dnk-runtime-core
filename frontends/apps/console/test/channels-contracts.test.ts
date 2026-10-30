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
        properties: { username: { title: "Логин", type: "string" } },
        required: ["username"],
      },
    },
  },
  credentialsSchema: {
    properties: {
      password: { type: "string", format: "password", writeOnly: true },
    },
    required: ["password"],
  },
};
test("Forms resolve platform-owned nested schemas and password metadata", () => {
  assert.equal(
    schemaFields(platform.configSchema, "settings")[0]?.key,
    "username",
  );
  assert.equal(schemaFields(platform.credentialsSchema)[0]?.secret, true);
  assert.equal(schemaFields(platform.configSchema)[0]?.readOnly, true);
});
test("Create serializes a complete independent secret snapshot; editing omits retained credentials", () => {
  const draft = draftFor(platform);
  draft.name = "Store";
  draft.settings.username = "seller";
  draft.credentials.password = "one-time-secret";
  const value = saveDraft(draft, platform);
  draft.credentials.password = "later-input";
  const body = createPayload(value);
  assert.equal(body.credentials.password, "one-time-secret");
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
      settings: { username: "seller", stock_sync: { allow_export: true } },
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
  assert.deepEqual(draft.credentials, { password: "" });
  assert.equal(draft.replaceCredentials, false);
  assert.equal(draft.allowStockExport, true);
  draft.allowStockExport = false;
  const saved = updatePayload(saveDraft(draft, platform), channel.revision);
  assert.deepEqual(saved.config.settings.stock_sync, { allow_export: false });
  assert.equal("allow_stock_export" in saved, false);
  assert.equal(channel.config.settings.stock_sync.allow_export, true);
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
