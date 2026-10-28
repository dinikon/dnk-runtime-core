import { test } from "node:test";
import assert from "node:assert/strict";
import {
  draftFor,
  saveDraft,
  schemaFields,
} from "../src/modules/channels/model/channel.schema.ts";
import {
  mapPublicationCard,
  mapPublicationItem,
  mapSyncRun,
} from "../src/modules/channels/api/publication.mapper.ts";
import type { Platform } from "../src/modules/channels/model/channel.types.ts";
import type { PublicationItemDto } from "../src/modules/channels/api/publication.dto.ts";
import {
  parsePublicationFilters,
  publicationPaginationQuery,
} from "../src/modules/channels/model/publication.filters.ts";
import { publicationThumbnail } from "../src/modules/channels/model/publication.thumbnail.ts";
import type { PublicationCard } from "../src/modules/channels/model/publication.types.ts";

const fixed: Platform = {
  kind: "prom",
  title: "Prom",
  configVersion: 1,
  supportedCapabilities: ["verify_connection", "publications"],
  configSchema: {
    properties: {
      endpoint: { const: "https://my.prom.ua" },
      settings: { $ref: "#/$defs/Settings" },
    },
    $defs: {
      Settings: {
        properties: {
          currency: { const: "UAH", default: "UAH", readOnly: true },
          locales: { type: "array", default: ["uk", "ru"], readOnly: true },
        },
      },
    },
  },
  credentialsSchema: {
    properties: { token: { type: "string", writeOnly: true } },
  },
};
test("Fixed locales retain array semantics and independent form snapshots", () => {
  const draft = draftFor(fixed);
  assert.deepEqual(draft.settings, { currency: "UAH", locales: ["uk", "ru"] });
  const saved = saveDraft(draft, fixed);
  assert.ok(Array.isArray(draft.settings.locales));
  draft.settings.locales.push("en");
  assert.deepEqual(saved.config.settings.locales, ["uk", "ru"]);
  assert.deepEqual(draftFor(fixed).settings.locales, ["uk", "ru"]);
  assert.equal(
    schemaFields(fixed.configSchema, "settings").find(
      (field) => field.key === "locales",
    )?.readOnly,
    true,
  );
});
test("WooCommerce schema exposes one currency and locale enum", () => {
  const fields = schemaFields({
    properties: {
      currency: { enum: ["UAH", "USD", "EUR"], default: "UAH" },
      locale: { enum: ["uk", "ru", "en"], default: "uk" },
    },
  });
  assert.deepEqual(fields[0]?.options, ["UAH", "USD", "EUR"]);
  assert.deepEqual(fields[1]?.options, ["uk", "ru", "en"]);
  assert.equal(fields[0]?.readOnly, false);
});
const item: PublicationItemDto = {
  id: "variant",
  external_id: "202",
  kind: "variant",
  title: null,
  sku: "BLACK-L",
  url: null,
  main_image_url: null,
  price: "9999999999.000000000001",
  regular_price: null,
  sale_price: "0.00",
  currency: "USD",
  quantity: "0",
  stock_mode: "parent",
  stock_source_publication_id: "root",
  availability: "out_of_stock",
  status: "publish",
  last_seen_at: "2026-10-28T10:00:00Z",
  stale_configuration: true,
};
test("Publication mapping preserves decimal strings, zero, missing translation and stock ownership", () => {
  const result = mapPublicationItem(item);
  assert.equal(result.price, item.price);
  assert.equal(result.salePrice, "0.00");
  assert.equal(result.quantity, "0");
  assert.equal(result.title, null);
  assert.equal(result.stockSourcePublicationId, "root");
  assert.equal(result.staleConfiguration, true);
});
test("Card mapping uses server membership without injecting a WooCommerce parent", () => {
  const result = mapPublicationCard({
    id: "root",
    root_kind: "variable",
    root_external_id: "201",
    root_sku: "PARENT",
    root_main_image_url: "https://cdn.example/parent.jpg",
    title: "T-shirt",
    selected_publication_id: "variant",
    items: [item],
    min_price: item.price,
    max_price: item.price,
    currency: "USD",
    last_seen_at: item.last_seen_at,
  });
  assert.deepEqual(
    result.items.map((value) => value.id),
    ["variant"],
  );
  assert.equal(result.selectedPublicationId, "variant");
  assert.equal(result.rootExternalId, "201");
  assert.equal(result.rootSku, "PARENT");
  assert.equal(result.rootMainImageUrl, "https://cdn.example/parent.jpg");
});
test("Interrupted sync keeps exact progress and recovery state", () => {
  const run = mapSyncRun({
    id: "run",
    config_revision: 2,
    revision: 4,
    status: "running",
    processed_count: 100,
    skipped_count: 3,
    pages_count: 1,
    automatic: true,
    error_code: null,
    created_at: "2026-10-28",
    started_at: "2026-10-28",
    finished_at: null,
    recovery_required: true,
  });
  assert.equal(run.recoveryRequired, true);
  assert.equal(run.processedCount, 100);
  assert.equal(run.skippedCount, 3);
  assert.equal(run.status, "running");
});

test("Publication URL parameters preserve filters and normalize page boundaries", () => {
  assert.deepEqual(
    parsePublicationFilters({
      q: "BLACK",
      locale: "ru",
      limit: "50",
      offset: "149",
    }),
    { search: "BLACK", locale: "ru", limit: 50, offset: 100 },
  );
  assert.deepEqual(parsePublicationFilters({ limit: "30", offset: "-50" }), {
    search: "",
    locale: "",
    limit: 25,
    offset: 0,
  });
  assert.equal(
    parsePublicationFilters({ limit: ["50", "100"], offset: "Infinity" }).limit,
    25,
  );
  assert.equal(parsePublicationFilters({ offset: "Infinity" }).offset, 0);
  assert.equal(
    parsePublicationFilters({ q: ["a", "b"], locale: ["ru", "uk"] }).search,
    "",
  );
});

test("Pagination changes reset to page one with the new size in a single URL patch", () => {
  const patch = publicationPaginationQuery({ page: 1, limit: 100 });
  assert.deepEqual(patch, { limit: "100", offset: undefined });
  const query = { q: "BLACK", locale: "uk", offset: "50", ...patch };
  assert.deepEqual(parsePublicationFilters(query), {
    search: "BLACK",
    locale: "uk",
    limit: 100,
    offset: 0,
  });
  assert.deepEqual(publicationPaginationQuery({ page: 3, limit: 50 }), {
    limit: "50",
    offset: "100",
  });
  assert.deepEqual(publicationPaginationQuery({ page: 1, limit: 25 }), {
    limit: undefined,
    offset: undefined,
  });
});

const thumbnailCard: PublicationCard = {
  id: "root",
  rootKind: "simple",
  rootExternalId: "201",
  rootSku: "PARENT",
  rootMainImageUrl: "https://cdn.example/parent.jpg",
  title: "T-shirt",
  selectedPublicationId: "selected",
  items: [
    {
      ...mapPublicationItem(item),
      id: "other",
      mainImageUrl: "https://cdn.example/other.jpg",
    },
    {
      ...mapPublicationItem(item),
      id: "selected",
      mainImageUrl: "https://cdn.example/selected.jpg",
    },
  ],
  minPrice: "0",
  maxPrice: "10",
  currency: "UAH",
  lastSeenAt: item.last_seen_at,
};

test("Thumbnail uses the selected position before other family members", () => {
  assert.equal(
    publicationThumbnail(thumbnailCard),
    "https://cdn.example/selected.jpg",
  );
  assert.equal(
    publicationThumbnail({
      ...thumbnailCard,
      items: thumbnailCard.items.map((position) =>
        position.id === "selected"
          ? { ...position, mainImageUrl: null }
          : position,
      ),
    }),
    "https://cdn.example/other.jpg",
  );
});

test("Thumbnail rejects invalid URLs and missing images without using external data", () => {
  for (const url of [
    null,
    "not-a-url",
    "javascript:alert(1)",
    "data:image/svg+xml,test",
    "https://secret:token@cdn.example/image.jpg",
  ]) {
    const card = {
      ...thumbnailCard,
      items: [{ ...mapPublicationItem(item), mainImageUrl: url }],
    };
    assert.equal(publicationThumbnail(card), null);
  }
  assert.equal(publicationThumbnail({ ...thumbnailCard, items: [] }), null);
});

test("WooCommerce thumbnails always use the parent, including missing or invalid parent photos", () => {
  const card = { ...thumbnailCard, rootKind: "variable" };
  assert.equal(publicationThumbnail(card), "https://cdn.example/parent.jpg");
  assert.equal(
    publicationThumbnail({ ...card, selectedPublicationId: "other" }),
    "https://cdn.example/parent.jpg",
  );
  for (const rootMainImageUrl of [null, "invalid", "javascript:alert(1)"]) {
    assert.equal(publicationThumbnail({ ...card, rootMainImageUrl }), null);
  }
});
