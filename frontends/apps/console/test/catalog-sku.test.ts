import assert from "node:assert/strict";
import test from "node:test";
import {
  catalogSkuSelectionToDto,
  setCatalogSkuResultFromDto,
} from "../src/modules/catalog/api/catalog-sku.mapper.ts";

test("SKU selection uses the inventory UUID while creation preserves the user's code for server normalization", () => {
  assert.deepEqual(
    catalogSkuSelectionToDto({
      mode: "existing",
      inventoryItemId: "inventory-uuid",
    }),
    { mode: "existing", inventory_item_id: "inventory-uuid" },
  );
  assert.deepEqual(
    catalogSkuSelectionToDto({ mode: "create", sku: " Straße-01 " }),
    { mode: "create", sku: " Straße-01 " },
  );
  assert.deepEqual(catalogSkuSelectionToDto({ mode: "clear" }), {
    mode: "clear",
  });
});

test("SKU assignment distinguishes a reused reference from newly created inventory", () => {
  const result = setCatalogSkuResultFromDto({
    item_id: "catalog-uuid",
    inventory_item_id: "inventory-uuid",
    sku: "strasse-01",
    inventory_item_created: false,
  });
  assert.deepEqual(result, {
    itemId: "catalog-uuid",
    inventoryItemId: "inventory-uuid",
    sku: "strasse-01",
    inventoryItemCreated: false,
  });
});

test("clearing SKU preserves explicit nulls and never substitutes the displayed code for the FK", () => {
  assert.deepEqual(
    setCatalogSkuResultFromDto({
      item_id: "catalog-uuid",
      inventory_item_id: null,
      sku: null,
      inventory_item_created: false,
    }),
    {
      itemId: "catalog-uuid",
      inventoryItemId: null,
      sku: null,
      inventoryItemCreated: false,
    },
  );
});
