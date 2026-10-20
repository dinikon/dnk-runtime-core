import { test } from "node:test";
import assert from "node:assert/strict";
import { DraftCreationIntents } from "../src/modules/channels/model/draft-creation-intents.ts";
import {
  confirmedDraft,
  editableDraft,
  draftFormIssue,
} from "../src/modules/channels/model/draft-form.ts";
import {
  createDraftPayload,
  mapPreview,
} from "../src/modules/channels/api/catalog-links.mapper.ts";
import { normalizeApiError } from "../src/modules/channels/api/channels.error.ts";
import type { DraftValues } from "../src/modules/channels/model/catalog-links.types.ts";
const values: DraftValues = {
  titles: { uk: "Товар" },
  sku: "SKU",
  regularPrice: "9007199254740993.123456",
  salePrice: "0",
  currency: "UAH",
  manageStock: true,
  quantity: "0",
  stockStatus: null,
  backorders: "no",
};
test("unknown outcome reuses exact immutable request even when form and source changed", () => {
  let serial = 0;
  const store = new DraftCreationIntents(() => `key-${++serial}`),
    draft = { ...values, titles: { ...values.titles } };
  const request = store.prepare("publication", 7, draft);
  draft.titles.uk = "Unsaved mutation";
  request.values.titles.uk = "Mutated returned copy";
  store.uncertain("publication");
  const retry = store.prepare("publication", 8, {
    ...draft,
    regularPrice: "5",
  });
  assert.equal(retry.requestKey, "key-1");
  assert.equal(retry.observedRevision, 7);
  assert.equal(retry.values.titles.uk, "Товар");
  assert.equal(retry.values.regularPrice, values.regularPrice);
  assert.deepEqual(store.unresolved(), ["publication"]);
  store.complete("publication");
  assert.equal(store.prepare("publication", 8, values).requestKey, "key-2");
});
test("context cleanup removes all unresolved creation intents", () => {
  const store = new DraftCreationIntents(() => "key");
  store.prepare("p", 1, values);
  store.uncertain("p");
  store.clear();
  assert.equal(store.get("p"), undefined);
});
test("Draft transfer keeps zero and exact money strings and excludes undeclared fields", () => {
  const payload = createDraftPayload({
    publicationId: "p",
    requestKey: "key",
    observedRevision: 3,
    values,
  });
  assert.equal(payload.values.regular_price, "9007199254740993.123456");
  assert.equal(payload.values.sale_price, "0");
  assert.equal(payload.values.quantity, "0");
  assert.equal(Object.hasOwn(payload, "tenant_id"), false);
  assert.equal(Object.hasOwn(payload.values, "status"), false);
  assert.equal(Object.hasOwn(payload.values, "extensions"), false);
});
test("manual presence and omitted prices do not leak hidden quantity, backorders or sale price", () => {
  const normalized = confirmedDraft(
    {
      ...values,
      manageStock: false,
      stockStatus: "out_of_stock",
      backorders: "yes",
    },
    false,
  );
  assert.equal(normalized.quantity, null);
  assert.equal(normalized.backorders, "no");
  assert.equal(normalized.regularPrice, null);
  assert.equal(normalized.salePrice, null);
  assert.equal(normalized.currency, null);
  assert.equal(draftFormIssue(normalized), null);
});
test("form never rounds fractional quantities or substitutes unknown availability", () => {
  assert.match(
    draftFormIssue({ ...values, quantity: "1.25" }) ?? "",
    /целое количество/,
  );
  assert.match(
    draftFormIssue({ ...values, manageStock: false, stockStatus: null }) ?? "",
    /статус наличия/,
  );
  const editable = editableDraft({
    ...values,
    quantity: "0E-12",
    salePrice: "100.000000000000",
  });
  assert.equal(editable.quantity, "0");
  assert.equal(editable.salePrice, "100");
  assert.equal(editable.regularPrice, values.regularPrice);
});
test("preview carries source identity so stale query data cannot initialize another publication", () => {
  const preview = mapPreview(
    {
      observed_revision: 4,
      values: {
        titles: { uk: "Товар" },
        sku: null,
        regular_price: "0",
        sale_price: null,
        currency: "UAH",
        manage_stock: false,
        quantity: null,
        stock_status: "unknown",
        backorders: "no",
        stock_confirmed: false,
      },
      issues: [{ field: "stock", message: "Выберите наличие" }],
      warnings: [],
      origins: {},
      main_image_url: null,
    },
    "publication-2",
    "uk",
  );
  assert.equal(preview.publicationId, "publication-2");
  assert.equal(preview.locale, "uk");
  assert.equal(preview.values.regularPrice, "0");
  assert.equal(preview.values.quantity, null);
});
test("owned Draft field errors are preserved without Axios body or config", () => {
  const raw = Object.assign(new Error("transport"), {
    isAxiosError: true,
    config: { data: { credentials: { token: "private" } } },
    response: {
      status: 422,
      data: {
        detail: {
          code: "invalid_catalog_draft",
          issues: [{ field: "sku", message: "SKU уже используется." }],
        },
      },
    },
  });
  const error = normalizeApiError(raw);
  assert.deepEqual(error.issues, [
    { field: "sku", message: "SKU уже используется." },
  ]);
  assert.equal(Object.hasOwn(error, "config"), false);
  assert.doesNotMatch(JSON.stringify(error), /private/);
});
