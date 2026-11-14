import assert from "node:assert/strict";
import test from "node:test";
import { effectScope, nextTick, ref } from "vue";
import { QueryClient } from "@tanstack/vue-query";
import { inventoryItemChangesToDto } from "../src/modules/inventory/api/inventory-item-edit.mapper.ts";
import {
  InventoryItemEditorDraft,
  inventoryItemEditSnapshot,
} from "../src/modules/inventory/model/inventory-item-editor-draft.ts";
import { useInventoryItemEditorDraft } from "../src/modules/inventory/model/use-inventory-item-editor-draft.ts";
import {
  validateInventoryItemEditor,
  inventoryItemErrorsForSnapshot,
} from "../src/modules/inventory/model/inventory-item-editor.validation.ts";
import { InventoryItemWriteError } from "../src/modules/inventory/model/inventory-item-write.errors.ts";
import { inventoryItemKeys } from "../src/modules/inventory/model/inventory-item.query-keys.ts";
import { itemPackagingKeys } from "../src/modules/inventory/model/item-packaging.query-keys.ts";
import {
  forgetInventoryItem,
  withoutInventoryItem,
  discardInaccessibleInventoryItem,
} from "../src/modules/inventory/model/inventory-item-removal.ts";
import { inventoryItemUpdateTenant } from "../src/modules/inventory/model/inventory-item-public.ts";
import { inventoryItemListReturnPath } from "../src/modules/inventory/model/inventory-item-navigation.ts";
import type { InventoryScope } from "../src/modules/inventory/model/inventory-scope.types.ts";
import type { InventoryItemDetails } from "../src/modules/inventory/model/inventory-item-settings.types.ts";
import type { InventoryItemsPage } from "../src/modules/inventory/model/inventory-item.types.ts";
const item: InventoryItemDetails = {
  id: "a",
  sku: "item",
  baseUom: "KG",
  quantityStep: "0.0000000000000000000000000000001",
  trackingMode: "NONE",
  expirationMode: "NONE",
  barcodes: [
    { id: "b1", barcode: "000AbC" },
    { id: "b2", barcode: "000abc" },
  ],
};
const uoms = [{ code: "KG", dimension: "MASS" }] as const;
const scope: InventoryScope = ["tenant", "user", "1"];
function draft(): InventoryItemEditorDraft {
  const result = new InventoryItemEditorDraft();
  result.reset(item);
  return result;
}
const input = () => ({ id: "a", scope, signal: new AbortController().signal });
test("changed-only PATCH preserves absence, explicit empty collection, order, case and Decimal", () => {
  assert.deepEqual(inventoryItemChangesToDto({}), {});
  assert.deepEqual(inventoryItemChangesToDto({ sku: " NEW ", barcodes: [] }), {
    sku: " NEW ",
    barcodes: [],
  });
  const codes = ["000abc", "000AbC"];
  const dto = inventoryItemChangesToDto({
    barcodes: codes,
    quantityStep: " 1.234567890123456789E-40 ",
  });
  codes.reverse();
  assert.deepEqual(dto, {
    barcodes: ["000abc", "000AbC"],
    quantity_rules: { step: "1.234567890123456789E-40" },
  });
});
test("editor sends only changed fields and treats barcode ordering and clearing as changes", () => {
  const state = draft();
  assert.deepEqual(state.changes, {});
  state.change({
    ...state.values!,
    sku: "new",
    barcodes: [...state.values!.barcodes].reverse(),
  });
  assert.deepEqual(state.changes, {
    sku: "new",
    barcodes: ["000abc", "000AbC"],
  });
  state.change({ ...state.values!, barcodes: [] });
  assert.deepEqual(state.changes.barcodes, []);
  state.reset(item);
  state.change({ ...state.values!, quantityStep: "2" });
  assert.deepEqual(state.changes, { quantityStep: "2" });
});
test("draft detaches arrays and uses persisted IDs plus stable unique local row keys", () => {
  const state = draft(),
    first = state.values!.barcodes[0]!.key;
  assert.equal(first, "saved:b1");
  state.addBarcode();
  const added = state.values!.barcodes.at(-1)!.key;
  const snap = inventoryItemEditSnapshot(state.values!);
  snap.barcodes[0]!.barcode = "external mutation";
  assert.equal(state.values!.barcodes[0]!.barcode, "000AbC");
  state.change({
    ...state.values!,
    barcodes: state.values!.barcodes.filter((row) => row.key !== added),
  });
  state.addBarcode();
  assert.notEqual(state.values!.barcodes.at(-1)!.key, added);
  assert.equal(state.values!.barcodes[0]!.key, first);
});
test("refetch keeps dirty identity/settings/barcodes and acknowledgement keeps newer values", () => {
  const state = draft();
  state.change({
    ...state.values!,
    sku: " SENT ",
    quantityStep: "2",
    barcodes: [{ key: "new:manual", barcode: " New " }],
  });
  const sent = inventoryItemEditSnapshot(state.values!);
  state.receive({ ...item, sku: "external" });
  assert.equal(state.values!.sku, " SENT ");
  state.change({
    ...state.values!,
    quantityStep: item.quantityStep,
    barcodes: [{ key: "new:manual", barcode: "Newer" }],
  });
  state.acknowledge(sent, {
    ...item,
    sku: "sent",
    quantityStep: "2.0",
    barcodes: [{ id: "server", barcode: "New" }],
  });
  assert.equal(state.values!.sku, "sent");
  assert.equal(state.values!.quantityStep, item.quantityStep);
  assert.deepEqual(state.changes, {
    quantityStep: item.quantityStep,
    barcodes: ["Newer"],
  });
});
test("acknowledging an unchanged collection receives canonical codes and server IDs", () => {
  const state = draft();
  state.change({
    ...state.values!,
    barcodes: [{ key: "new:1", barcode: " new " }],
  });
  state.acknowledge(inventoryItemEditSnapshot(state.values!), {
    ...item,
    barcodes: [{ id: "server-id", barcode: "new" }],
  });
  assert.deepEqual(state.values!.barcodes, [
    { key: "saved:server-id", barcode: "new" },
  ]);
  assert.equal(state.dirty, false);
});
test("checking an uncertain PATCH rebases against fresh server state without erasing input", () => {
  const state = draft();
  state.change({ ...state.values!, sku: "new", barcodes: [] });
  state.rebase({ ...item, sku: "new" });
  assert.equal(state.values!.sku, "new");
  assert.deepEqual(state.changes, { barcodes: [] });
  state.clear();
  assert.equal(state.values, null);
  assert.equal(state.dirty, false);
});
test("validation keeps barcode case and leading zeros, rejects trimmed duplicates and blank rows", () => {
  const state = draft();
  assert.deepEqual(validateInventoryItemEditor(state.values!, [], false), {
    fields: {},
    barcodeRows: {},
  });
  state.change({
    ...state.values!,
    sku: " ",
    barcodes: [
      { key: "a", barcode: "001" },
      { key: "b", barcode: " 001 " },
      { key: "c", barcode: "" },
    ],
  });
  const errors = validateInventoryItemEditor(state.values!, uoms, true);
  assert.ok(errors.fields.sku);
  assert.deepEqual(Object.keys(errors.barcodeRows), ["c", "a", "b"]);
  assert.ok(
    validateInventoryItemEditor(state.values!, [], true).fields.baseUom,
  );
});
test("indexed server errors follow sent row identity after reordering and ignore newer typing", () => {
  const state = draft(),
    sent = inventoryItemEditSnapshot(state.values!);
  const error = new InventoryItemWriteError(
    "invalid",
    422,
    { sku: "SKU" },
    { 0: "bad first", 1: "bad second" },
  );
  state.change({
    ...state.values!,
    sku: "new",
    barcodes: [{ ...sent.barcodes[1]!, barcode: "newer" }, sent.barcodes[0]!],
  });
  assert.deepEqual(inventoryItemErrorsForSnapshot(error, sent, state.values!), {
    fields: {},
    barcodeRows: { "saved:b1": "bad first" },
  });
  assert.deepEqual(
    inventoryItemErrorsForSnapshot(
      new InventoryItemWriteError("conflict", 409),
      sent,
      state.values!,
    ),
    { fields: {}, barcodeRows: {} },
  );
});
test("editor resets on identity changes and blocks refetch during requests", async () => {
  const effects = effectScope(),
    identity = ref("a"),
    pending = ref(false),
    source = ref<InventoryItemDetails | undefined>(item);
  const state = effects.run(() =>
    useInventoryItemEditorDraft(() => source.value, identity, pending),
  )!;
  try {
    state.change({ ...state.values.value!, sku: "dirty" });
    pending.value = true;
    source.value = { ...item, sku: "external" };
    assert.equal(state.values.value?.sku, "dirty");
    identity.value = "b";
    source.value = undefined;
    pending.value = false;
    await nextTick();
    assert.equal(state.values.value, null);
    source.value = item;
    await nextTick();
    assert.equal(state.dirty.value, false);
    state.clear();
    assert.equal(state.values.value, null);
  } finally {
    effects.stop();
  }
});
test("update integration accepts only matching, non-aborted Inventory PATCH context", () => {
  const value = input(),
    key = inventoryItemKeys.update(scope, "a");
  assert.equal(inventoryItemUpdateTenant(key, value), "tenant");
  for (const wrong of [
    undefined,
    {},
    { ...value, id: "other" },
    { ...value, scope: ["other", "user", "1"] },
    { ...value, scope: ["tenant", "user", "1", "extra"] },
  ])
    assert.equal(inventoryItemUpdateTenant(key, wrong), null);
  assert.equal(
    inventoryItemUpdateTenant(inventoryItemKeys.delete(scope, "a"), value),
    null,
  );
  const controller = new AbortController();
  controller.abort();
  assert.equal(
    inventoryItemUpdateTenant(key, { ...value, signal: controller.signal }),
    null,
  );
});
const page: InventoryItemsPage = {
  items: [item, { ...item, id: "other" }],
  total: 51,
  offset: 0,
  limit: 50,
};
test("confirmed removal changes totals only where ID exists and never decrements twice", () => {
  const result = withoutInventoryItem(page, "a")!;
  assert.equal(result.total, 50);
  assert.equal(withoutInventoryItem(result, "a"), result);
  assert.equal(withoutInventoryItem(page, "missing"), page);
  assert.equal(withoutInventoryItem(undefined, "a"), undefined);
});
test("removal clears exact card and own packaging, isolates other items and other sessions", async () => {
  const cache = new QueryClient(),
    key = inventoryItemKeys.list(scope, { search: "", offset: 0, limit: 50 }),
    detail = inventoryItemKeys.detail(scope, "a"),
    own = itemPackagingKeys.detail(scope, "a", "p"),
    other = itemPackagingKeys.detail(scope, "other", "p"),
    foreign = inventoryItemKeys.list(["tenant", "other", "2"], key[6]);
  try {
    cache.setQueryData(key, page);
    cache.setQueryData(detail, item);
    cache.setQueryData(own, { id: "p" });
    cache.setQueryData(other, { id: "p" });
    cache.setQueryData(foreign, page);
    await forgetInventoryItem(cache, input(), () => true);
    assert.equal(cache.getQueryData(detail), undefined);
    assert.equal(cache.getQueryData(own), undefined);
    assert.deepEqual(cache.getQueryData(other), { id: "p" });
    assert.deepEqual(cache.getQueryData(foreign), page);
    assert.equal(cache.getQueryData<InventoryItemsPage>(key)?.total, 50);
    assert.equal(cache.getQueryState(key)?.isInvalidated, true);
  } finally {
    cache.clear();
  }
});
test("late list/detail/packaging reads cannot resurrect a removed item", async () => {
  const cache = new QueryClient(),
    key = inventoryItemKeys.list(scope, { search: "", offset: 0, limit: 50 }),
    detail = inventoryItemKeys.detail(scope, "a"),
    packaging = itemPackagingKeys.detail(scope, "a", "p");
  let releases: Array<() => void> = [],
    aborted = 0;
  try {
    cache.setQueryData(key, page);
    cache.setQueryData(detail, item);
    cache.setQueryData(packaging, item);
    const reads = [key, detail, packaging].map((queryKey) =>
      cache
        .fetchQuery({
          queryKey,
          queryFn: ({ signal }) => {
            signal.addEventListener("abort", () => aborted++);
            return new Promise((resolve) =>
              releases.push(() => resolve(queryKey === key ? page : item)),
            );
          },
        })
        .catch(() => undefined),
    );
    await forgetInventoryItem(cache, input(), () => true);
    for (const release of releases) release();
    await Promise.all(reads);
    assert.equal(aborted, 3);
    assert.equal(cache.getQueryData(detail), undefined);
    assert.equal(cache.getQueryData(packaging), undefined);
    assert.deepEqual(
      cache.getQueryData<InventoryItemsPage>(key)?.items.map((row) => row.id),
      ["other"],
    );
  } finally {
    releases = [];
    cache.clear();
  }
});
test("context changes stop late cache writes; access denial discards inaccessible projections", async () => {
  const cache = new QueryClient(),
    key = inventoryItemKeys.list(scope, { search: "", offset: 0, limit: 50 });
  try {
    cache.setQueryData(key, page);
    let checks = 0;
    await forgetInventoryItem(cache, input(), () => ++checks === 1);
    assert.deepEqual(cache.getQueryData(key), page);
    await discardInaccessibleInventoryItem(cache, input(), () => false);
    assert.deepEqual(cache.getQueryData(key), page);
    await discardInaccessibleInventoryItem(cache, input(), () => true);
    assert.equal(cache.getQueryData(key), undefined);
  } finally {
    cache.clear();
  }
});
test("delete return preserves own list query/hash and sends Catalog origins to Inventory list", () => {
  assert.equal(
    inventoryItemListReturnPath(
      "/inventory/items?search=A&page=2&limit=20#table",
    ),
    "/inventory/items?search=A&page=2&limit=20#table",
  );
  for (const value of [
    "/catalog/items/a?locale=ru",
    "/inventory/items/a",
    "//outside",
    "https://outside",
    "/inventory/items\\evil",
  ])
    assert.equal(inventoryItemListReturnPath(value), "/inventory/items");
  for (const status of [null, 408, 500, 503])
    assert.equal(
      new InventoryItemWriteError("unknown", status).uncertain,
      true,
    );
  for (const status of [403, 404, 409, 422])
    assert.equal(
      new InventoryItemWriteError("rejected", status).uncertain,
      false,
    );
});
