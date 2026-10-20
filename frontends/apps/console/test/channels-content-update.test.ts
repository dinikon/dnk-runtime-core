import assert from "node:assert/strict";
import test from "node:test";
import {
  mapContentUpdate,
  contentUpdateConfirmPayload,
  contentUpdateStartPayload,
} from "../src/modules/channels/api/content-updates.mapper.ts";
import {
  canConfirmContentUpdate,
  contentUpdateActive,
} from "../src/modules/channels/model/content-update.presentation.ts";
import { channelsKeys } from "../src/modules/channels/model/channels.query-keys.ts";
import type { GetContentUpdateResponseDto } from "../src/modules/channels/api/content-updates.dto.ts";
const dto: GetContentUpdateResponseDto = {
  id: "run",
  channel_id: "channel",
  status: "ready",
  revision: 4,
  sequence: 1,
  preview_hash: "hash",
  created_at: "2026-10-19T10:00:00Z",
  expires_at: "2026-10-20T10:00:00Z",
  confirmed_at: null,
  outbound_enabled: false,
  interrupted: false,
  items: [
    {
      publication_id: "pub",
      catalog_item_id: "item",
      external_id: "10",
      desired: [{ locale: "uk", title: "New", body: "<p>New</p>" }],
      observed: [{ locale: "uk", title: "Old", body: null }],
      status: "ready",
      issues: [],
      attempts: 0,
    },
  ],
};
test("mapping preserves exact locale/content and isolates mutable API arrays", () => {
  const run = mapContentUpdate(dto);
  assert.equal(run.items[0]!.observed[0]!.body, null);
  assert.equal(run.items[0]!.desired[0]!.locale, "uk");
  run.items[0]!.desired[0]!.title = "Edited model";
  assert.equal(dto.items[0]!.desired[0]!.title, "New");
});
test("manual confirmation requires permission, unchanged preview state and a nonexpired snapshot", () => {
  const run = mapContentUpdate(dto),
    now = Date.parse("2026-10-19T12:00:00Z");
  assert.equal(canConfirmContentUpdate(run, now), false);
  assert.equal(
    canConfirmContentUpdate({ ...run, outboundEnabled: true }, now),
    true,
  );
  assert.equal(
    canConfirmContentUpdate(
      { ...run, outboundEnabled: true },
      Date.parse(dto.expires_at),
    ),
    false,
  );
  assert.equal(
    canConfirmContentUpdate(
      { ...run, outboundEnabled: true, confirmedAt: "accepted" },
      now,
    ),
    false,
  );
  assert.equal(
    canConfirmContentUpdate(
      { ...run, outboundEnabled: true, status: "blocked" },
      now,
    ),
    false,
  );
});
test("confirmation payload cannot introduce text overrides or arbitrary platform fields", () => {
  assert.deepEqual(
    contentUpdateConfirmPayload({
      runId: "run",
      revision: 4,
      previewHash: "hash",
    }),
    { expected_revision: 4, preview_hash: "hash" },
  );
  assert.deepEqual(
    contentUpdateStartPayload({
      runId: "run",
      channelId: "channel",
      publicationIds: ["b", "a"],
    }),
    { run_id: "run", publication_ids: ["a", "b"] },
  );
});
test("polling stops for terminal or interrupted runs; keys include actor/tenant scope", () => {
  const run = mapContentUpdate(dto);
  assert.equal(contentUpdateActive({ ...run, status: "running" }), true);
  assert.equal(
    contentUpdateActive({ ...run, status: "running", interrupted: true }),
    false,
  );
  assert.equal(contentUpdateActive({ ...run, status: "succeeded" }), false);
  assert.notDeepEqual(
    channelsKeys.contentUpdate("tenant:actor1", "run"),
    channelsKeys.contentUpdate("tenant:actor2", "run"),
  );
});
