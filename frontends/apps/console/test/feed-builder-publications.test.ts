import { test } from "node:test";
import assert from "node:assert/strict";
import {
  publicationReferenceKey,
  mergePublicationChoices,
  togglePublicationChoice,
} from "../src/modules/feed-builder/model/feed-publication.selection.ts";
import {
  mapPublication,
  mapPublications,
  addPublicationsPayload,
  mapAddedPublications,
  mapVariantSelection,
} from "../src/modules/feed-builder/api/feed-publication.mapper.ts";
import { publicationKeys } from "../src/modules/feed-builder/model/feed-publication.query-keys.ts";
import type {
  PublicationChoice,
  PublicationFilters,
} from "../src/modules/feed-builder/model/feed-publication.types.ts";
import type { PublicationDTO } from "../src/modules/feed-builder/api/feed-publication.dto.ts";
const choice = (
  id: string,
  variant: string | null = null,
): PublicationChoice => ({
  itemId: id,
  variantId: variant,
  kind: variant ? "variant" : "simple",
  title: "Товар",
  sku: variant,
});
test("Selection identifies SIMPLE and each chosen variant independently, survives pages and deduplicates overlap with select-all", () => {
  const simple = choice("simple"),
    white = choice("family", "white"),
    black = choice("family", "black");
  let selected = togglePublicationChoice([], simple);
  selected = togglePublicationChoice(selected, white);
  selected = mergePublicationChoices(selected, [white, black]);
  assert.deepEqual(
    selected.map(publicationReferenceKey),
    [simple, white, black].map(publicationReferenceKey),
  );
  assert.deepEqual(togglePublicationChoice(selected, white), [simple, black]);
  assert.notEqual(
    publicationReferenceKey(simple),
    publicationReferenceKey(choice("simple", "variant")),
  );
  const full = Array.from({ length: 100 }, (_, i) => choice(String(i)));
  assert.throws(() => mergePublicationChoices(full, [choice("overflow")]));
  assert.equal(full.length, 100);
});
test("HTTP payload is an explicit frozen set of references, including NULL for SIMPLE", () => {
  const payload = addPublicationsPayload({
    feedId: "feed",
    expectedFeedVersion: 7,
    references: [choice("simple"), choice("family", "white")],
  });
  assert.deepEqual(payload, {
    expected_feed_version: 7,
    item_references: [
      { catalog_item_id: "simple", catalog_variant_id: null },
      { catalog_item_id: "family", catalog_variant_id: "white" },
    ],
  });
  const added = mapAddedPublications({
    feed_id: "feed",
    feed_version: 7,
    items: [
      {
        id: "stable",
        catalog_item_id: "family",
        catalog_variant_id: "white",
        status: "ARCHIVED",
        version: 9,
        outcome: "EXISTING",
      },
    ],
  });
  assert.equal(added.items[0]!.id, "stable");
  assert.equal(added.items[0]!.status, "ARCHIVED");
  assert.equal(added.items[0]!.outcome, "EXISTING");
  assert.deepEqual(
    mapVariantSelection({
      items: [
        {
          catalog_item_id: "family",
          catalog_variant_id: "white",
          title: null,
          sku: "WHITE",
        },
      ],
    }),
    [
      {
        itemId: "family",
        variantId: "white",
        title: "WHITE",
        sku: "WHITE",
        kind: "variant",
      },
    ],
  );
});
test("Read models preserve missing Catalog, passive identity and actual publication version without inventing readiness", () => {
  const dto: PublicationDTO = {
    id: "pub",
    feed_id: "feed",
    catalog_item_id: "family",
    catalog_variant_id: "white",
    status: "PAUSED",
    version: 9,
    title: null,
    parent_title: "Топ",
    sku: "",
    kind: null,
    source_available: false,
    overrides_count: 2,
    created_at: "2026-11-22T12:00:00Z",
    updated_at: "2026-11-22T12:01:00Z",
  };
  const model = mapPublication(dto);
  assert.equal(model.sourceAvailable, false);
  assert.equal(model.sku, "");
  assert.equal(model.variantId, "white");
  assert.equal(model.version, 9);
  assert.equal("readiness" in model, false);
  const page = mapPublications({
    feed_id: "feed",
    feed_version: 7,
    feed_status: "DRAFT",
    items: [dto],
    total: 1,
    counts: { PAUSED: 1, ARCHIVED: 3 },
  });
  assert.equal(page.counts.ARCHIVED, 3);
  assert.equal(page.feedVersion, 7);
});
test("Keys isolate feed, locale, status, pagination and tenant/user/session", () => {
  const f: PublicationFilters = {
    locale: "uk",
    search: "WHITE",
    status: "",
    offset: 0,
    limit: 25,
  };
  const key = publicationKeys.list(["a", "user", "1"], "feed", f);
  for (const other of [
    publicationKeys.list(["b", "user", "1"], "feed", f),
    publicationKeys.list(["a", "other", "1"], "feed", f),
    publicationKeys.list(["a", "user", "2"], "feed", f),
    publicationKeys.list(["a", "user", "1"], "other", f),
    publicationKeys.list(["a", "user", "1"], "feed", { ...f, offset: 25 }),
    publicationKeys.list(["a", "user", "1"], "feed", {
      ...f,
      status: "ARCHIVED",
    }),
  ])
    assert.notDeepEqual(key, other);
});
