import { test } from "node:test";
import assert from "node:assert/strict";
import {
  batchActive,
  batchPolling,
  scheduleDateLabel,
} from "../src/modules/channels/model/batch-export.presentation.ts";
import {
  mapBatchStatus,
  schedulePayload,
  publicationExportPayload,
} from "../src/modules/channels/api/batch-export.mapper.ts";
import { channelsKeys } from "../src/modules/channels/model/channels.query-keys.ts";

test("uncertain delivery blocks a second batch without endlessly polling", () => {
  assert.equal(batchActive("unknown"), true);
  assert.equal(batchPolling("unknown"), false);
  assert.equal(batchPolling("submitting"), true);
  assert.equal(batchActive("partial"), false);
  assert.equal(batchActive("prepared"), false);
  assert.equal(batchPolling("prepared"), false);
  assert.equal(mapBatchStatus("prepared"), "prepared");
  assert.equal(mapBatchStatus("future-provider-state"), "unknown");
});
test("policy and export permissions do not transmit resource settings or Catalog values", () => {
  assert.deepEqual(
    schedulePayload({
      channelId: "channel",
      enabled: true,
      hour: 3,
      minute: 15,
      timezone: "Europe/Kyiv",
      expectedRevision: 7,
    }),
    {
      enabled: true,
      hour: 3,
      minute: 15,
      timezone: "Europe/Kyiv",
      expected_revision: 7,
    },
  );
  assert.deepEqual(
    publicationExportPayload({
      channelId: "channel",
      enabled: false,
      items: [{ representationId: "representation", expectedRevision: 9 }],
    }),
    {
      enabled: false,
      items: [{ representation_id: "representation", expected_revision: 9 }],
    },
  );
});
test("batch pagination and export filters are separated by tenant/session cache scope", () => {
  assert.notDeepEqual(
    channelsKeys.batchDetail("tenant-a:user", {
      runId: "same",
      offset: 0,
      limit: 50,
    }),
    channelsKeys.batchDetail("tenant-b:user", {
      runId: "same",
      offset: 0,
      limit: 50,
    }),
  );
  assert.notDeepEqual(
    channelsKeys.batchDetail("tenant:user", {
      runId: "same",
      offset: 0,
      limit: 50,
    }),
    channelsKeys.batchDetail("tenant:user", {
      runId: "same",
      offset: 50,
      limit: 50,
    }),
  );
  assert.notDeepEqual(
    channelsKeys.publications("tenant:user", "connection", {
      search: "",
      stockStatus: "",
      offset: 0,
      limit: 20,
      exportStatus: "enabled",
    }),
    channelsKeys.publications("tenant:user", "connection", {
      search: "",
      stockStatus: "",
      offset: 0,
      limit: 20,
      exportStatus: "disabled",
    }),
  );
});

test("next run is displayed in the policy timezone rather than the browser timezone", () => {
  assert.match(scheduleDateLabel("2026-10-20T12:00:00Z", "UTC"), /12:00/);
  assert.match(
    scheduleDateLabel("2026-10-20T12:00:00Z", "Europe/Kyiv"),
    /15:00/,
  );
});
