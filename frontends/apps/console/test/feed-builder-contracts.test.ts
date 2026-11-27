import { test } from "node:test";
import assert from "node:assert/strict";
import {
  feedDraft,
  draftSettings,
  feedChanges,
  acknowledgeFeedDraft,
  validateFeedDraft,
} from "../src/modules/feed-builder/model/feed.draft.ts";
import {
  createFeedPayload,
  patchFeedPayload,
  mapFeed,
  mapFeedListItem,
} from "../src/modules/feed-builder/api/feed.mapper.ts";
import {
  FeedApiError,
  type Feed,
} from "../src/modules/feed-builder/model/feed.types.ts";
import {
  feedErrorMessage,
  isUncertainCreate,
} from "../src/modules/feed-builder/model/feed.errors.ts";
const initial = feedDraft();
const csv = draftSettings({
  ...initial,
  name: "  Prom  ",
  code: " prom ",
  format: "csv",
  delimiter: ";",
  includeHeader: false,
});
const feed: Feed = {
  ...csv,
  id: "feed-1",
  status: "DRAFT",
  version: 7,
  createdAt: "2026-11-22T10:30:00Z",
  updatedAt: "2026-11-22T10:35:00Z",
  schema: {
    schema_format_version: 2,
    fields: [{ amount: "123456789.123456789" }],
  },
};
test("Creation requires an explicit format and serializes only supported create properties", () => {
  assert.equal(initial.format, "");
  assert.ok(validateFeedDraft(initial).format);
  assert.throws(() => draftSettings(initial));
  assert.deepEqual(createFeedPayload(csv), {
    name: "Prom",
    code: "prom",
    export_settings: {
      format_settings: {
        format: "csv",
        delimiter: ";",
        encoding: "utf-8",
        include_header: false,
      },
      product_mode: "VARIABLE_TO_SINGLE",
      validation_policy: "STRICT",
    },
  });
  assert.equal("schema" in createFeedPayload(feed), false);
  assert.equal("status" in createFeedPayload(feed), false);
});
test("Changing format replaces the entire settings object without leaking CSV values into XML", () => {
  const draft = {
    ...feedDraft(feed),
    format: "xml" as const,
    rootName: "offers",
    itemName: "offer",
  };
  const changes = feedChanges(feed, draftSettings(draft));
  assert.deepEqual(
    patchFeedPayload({ id: feed.id, expectedVersion: feed.version, changes }),
    {
      expected_version: 7,
      export_settings: {
        format_settings: {
          format: "xml",
          root_name: "offers",
          item_name: "offer",
          encoding: "utf-8",
        },
        product_mode: "VARIABLE_TO_SINGLE",
        validation_policy: "STRICT",
      },
    },
  );
  const xml = { ...feed, exportSettings: draftSettings(draft).exportSettings };
  assert.equal(feedDraft(xml).rootName, "offers");
  assert.equal(feedDraft(xml).format, "xml");
});
test("Saving the policy preserves it in the settings payload and the reloaded draft", () => {
  assert.equal(feedDraft().validationPolicy, "STRICT");
  const next = draftSettings({
    ...feedDraft(feed),
    validationPolicy: "SKIP_INVALID",
  });
  const updated = patchFeedPayload({
    id: feed.id,
    expectedVersion: feed.version,
    changes: feedChanges(feed, next),
  });
  assert.equal(updated.export_settings?.validation_policy, "SKIP_INVALID");
  const saved = mapFeed({
    ...createFeedPayload(next),
    id: feed.id,
    status: feed.status,
    version: feed.version + 1,
    schema: feed.schema,
    created_at: feed.createdAt,
    updated_at: feed.updatedAt,
  });
  assert.equal(feedDraft(saved).validationPolicy, "SKIP_INVALID");
  assert.deepEqual(feedChanges(saved, draftSettings(feedDraft(saved))), {});
});
test("PATCH is a minimal diff with a server version, including false and no automatic status/schema edits", () => {
  assert.deepEqual(feedChanges(feed, csv), {});
  const body = patchFeedPayload({
    id: feed.id,
    expectedVersion: 7,
    changes: feedChanges(feed, { ...csv, name: "Retail" }),
  });
  assert.deepEqual(body, { expected_version: 7, name: "Retail" });
  assert.equal("schema" in body, false);
  assert.equal("status" in body, false);
});
test("Restored responses preserve schema Decimal strings, nested settings, dates and versions", () => {
  const wire = {
    ...createFeedPayload(csv),
    id: feed.id,
    status: feed.status,
    version: 7,
    created_at: feed.createdAt,
    updated_at: feed.updatedAt,
    schema: structuredClone(feed.schema),
  };
  const restored = mapFeed(wire);
  assert.deepEqual(restored, feed);
  wire.schema.root = null;
  assert.deepEqual(restored.schema, feed.schema);
  assert.deepEqual(
    mapFeedListItem({
      id: feed.id,
      name: feed.name,
      code: feed.code,
      status: "ARCHIVED",
      version: 8,
      format: "csv",
      fields_count: 4,
      created_at: feed.createdAt,
      updated_at: feed.updatedAt,
    }),
    {
      id: feed.id,
      name: feed.name,
      code: feed.code,
      status: "ARCHIVED",
      version: 8,
      format: "csv",
      fieldsCount: 4,
      createdAt: feed.createdAt,
      updatedAt: feed.updatedAt,
    },
  );
});
test("Drafts are independent of query data; acknowledging a save preserves input entered during that request", () => {
  const sent = feedDraft(feed),
    current = { ...sent, name: "Typed while saving" };
  const saved = { ...feed, version: 8 };
  assert.deepEqual(acknowledgeFeedDraft(current, sent, saved), current);
  assert.deepEqual(acknowledgeFeedDraft(sent, sent, saved), feedDraft(saved));
  sent.delimiter = "|";
  assert.equal(
    feed.exportSettings.formatSettings.format === "csv" &&
      feed.exportSettings.formatSettings.delimiter,
    ";",
  );
});
test("Form validates names/codes, XML identifiers and CSV delimiters without imposing inactive-format rules", () => {
  const draft = { ...feedDraft(feed) };
  assert.deepEqual(validateFeedDraft(draft), {});
  for (const code of ["Title", "1code", "a b", "a".repeat(65)])
    assert.ok(validateFeedDraft({ ...draft, code }).code);
  assert.ok(validateFeedDraft({ ...draft, name: "bad\nname" }).name);
  assert.ok(validateFeedDraft({ ...draft, name: "a".repeat(256) }).name);
  for (const delimiter of ['"', "\n", "\u0000", "ab", "\u2028"])
    assert.ok(validateFeedDraft({ ...draft, delimiter }).delimiter);
  assert.deepEqual(
    validateFeedDraft({ ...draft, delimiter: "\t", rootName: "not:xml" }),
    {},
  );
  assert.ok(
    validateFeedDraft({ ...draft, format: "xml", rootName: "not:xml" })
      .rootName,
  );
  assert.deepEqual(
    validateFeedDraft({
      ...draft,
      format: "xml",
      delimiter: "invalid",
      rootName: "_catalog",
      itemName: "offer.item-1",
    }),
    {},
  );
});
test("Conflict and ambiguous create messages distinguish safe corrections from potentially committed creation", () => {
  assert.match(feedErrorMessage(new FeedApiError(409), true), /код уже занят/);
  assert.match(feedErrorMessage(new FeedApiError(409)), /Ваш ввод сохранён/);
  assert.match(feedErrorMessage(new FeedApiError(403)), /прав/);
  assert.match(feedErrorMessage(new FeedApiError(404)), /не найден/);
  assert.equal(isUncertainCreate(new FeedApiError(422)), false);
  assert.equal(isUncertainCreate(new FeedApiError(500)), true);
  assert.equal(isUncertainCreate(new FeedApiError(undefined)), true);
});
