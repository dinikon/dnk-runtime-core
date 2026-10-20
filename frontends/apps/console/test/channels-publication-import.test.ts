import { test } from "node:test";
import assert from "node:assert/strict";
import {
  copyImportValues,
  moveImportImage,
  removeImportImage,
  restorePublicationImportDraft,
} from "../src/modules/channels/model/publication-import-draft.ts";
import { copyDraftValues } from "../src/modules/channels/model/draft-creation-intents.ts";
import type { ImportDraftValues } from "../src/modules/channels/model/publication-import.types.ts";
const values: ImportDraftValues = {
  titles: { uk: "Назва", ru: "Название" },
  descriptions: { uk: "<p>Опис</p>", ru: "<p>Описание</p>" },
  gallery: ["a", "b"],
  primaryImageId: "a",
  sku: "S",
  regularPrice: "123.450000",
  salePrice: "100",
  currency: "UAH",
  manageStock: true,
  quantity: "8",
  stockStatus: null,
  backorders: "no",
};
test("gallery order and main image survive moves; explicit exclusion chooses a remaining main", () => {
  const reordered = moveImportImage(values, "b", -1);
  assert.deepEqual(reordered.gallery, ["b", "a"]);
  assert.equal(reordered.primaryImageId, "a");
  assert.deepEqual(removeImportImage(reordered, "a").gallery, ["b"]);
  assert.equal(removeImportImage(reordered, "a").primaryImageId, "b");
  assert.equal(
    removeImportImage(removeImportImage(values, "a"), "b").primaryImageId,
    null,
  );
  assert.deepEqual(values.gallery, ["a", "b"]);
});
test("content and gallery are deeply detached for frozen creation retries", () => {
  const copy = copyDraftValues(values);
  copy.titles.uk = "Changed";
  copy.descriptions!.uk = "Changed";
  copy.gallery!.reverse();
  assert.equal(values.descriptions.uk, "<p>Опис</p>");
  assert.deepEqual(values.gallery, ["a", "b"]);
  const imported = copyImportValues(values);
  imported.descriptions.ru = "Other";
  assert.equal(values.descriptions.ru, "<p>Описание</p>");
});
test("reload restores exact uncertain intent including preparation revision and gallery", () => {
  const input = {
    publicationId: "p",
    preparationId: "prep",
    preparationRevision: 9,
    requestKey: "key",
    observedRevision: 3,
    values,
  };
  const record = {
    version: 1,
    expiresAt: "2026-10-19T00:00:00Z",
    baseline: JSON.stringify(values),
    values,
    intent: input,
    uncertain: true,
  };
  assert.deepEqual(
    restorePublicationImportDraft(
      JSON.stringify(record),
      Date.parse("2026-10-18T00:00:00Z"),
    )?.intent,
    input,
  );
  assert.deepEqual(
    restorePublicationImportDraft(
      JSON.stringify(record),
      Date.parse("2026-10-20T00:00:00Z"),
    )?.intent,
    input,
  );
  assert.equal(
    restorePublicationImportDraft(
      JSON.stringify({ ...record, uncertain: false }),
      Date.parse("2026-10-20T00:00:00Z"),
    ),
    null,
  );
  assert.equal(
    restorePublicationImportDraft('{"version":1,"values":{"evil":true}}'),
    null,
  );
  assert.equal(restorePublicationImportDraft("bad json"), null);
});
test("price transfer choice survives reload independently of source price fields", () => {
  const draft = { ...values, copyPrices: false };
  const record = {
    version: 1,
    expiresAt: "2026-10-19T00:00:00Z",
    baseline: JSON.stringify(values),
    values: draft,
    intent: null,
    uncertain: false,
  };
  assert.equal(
    restorePublicationImportDraft(
      JSON.stringify(record),
      Date.parse("2026-10-18T00:00:00Z"),
    )?.values.copyPrices,
    false,
  );
});
