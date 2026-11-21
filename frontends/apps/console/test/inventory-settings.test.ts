import assert from "node:assert/strict";
import test from "node:test";
import { inventoryItemChangesToDto } from "../src/modules/inventory/api/inventory-item-edit.mapper.ts";
import {
  inventoryItemDetailsFromDto,
  inventoryUomsFromDto,
} from "../src/modules/inventory/api/inventory-item-settings.mapper.ts";
import { validateInventorySettings } from "../src/modules/inventory/model/inventory-item-settings.validation.ts";
import {
  inventoryItemReturnPath,
  inventoryItemEditLocation,
} from "../src/modules/inventory/model/inventory-item-navigation.ts";
import type { InventoryItemSettings } from "../src/modules/inventory/model/inventory-item-settings.types.ts";

const defaults: InventoryItemSettings = {
  baseUom: "PCS",
  quantityStep: "1",
  trackingMode: "NONE",
  expirationMode: "NONE",
};
const uoms = [
  { code: "PCS", dimension: "COUNT" },
  { code: "KG", dimension: "MASS" },
] as const;

test("detail mapping and settings PATCH retain exact decimals and omit unrelated fields", () => {
  const value = inventoryItemDetailsFromDto({
    id: "item",
    sku: "sku",
    base_uom: "KG",
    quantity_rules: { step: "1.234567890123456789E-40" },
    tracking_mode: "LOT",
    expiration_mode: "REQUIRED",
    barcodes: [{ id: "barcode-id", barcode: "000a" }],
  });
  const payload = inventoryItemChangesToDto({
    baseUom: value.baseUom,
    quantityStep: value.quantityStep,
    trackingMode: value.trackingMode,
    expirationMode: value.expirationMode,
  });
  assert.deepEqual(payload, {
    base_uom: "KG",
    quantity_rules: { step: "1.234567890123456789E-40" },
    tracking_mode: "LOT",
    expiration_mode: "REQUIRED",
  });
  assert.deepEqual(value.barcodes, [{ id: "barcode-id", barcode: "000a" }]);
  assert.deepEqual(inventoryUomsFromDto({ items: [...uoms] }), uoms);
});

test("validation accepts exact positive decimals, including API powers without floating point", () => {
  for (const quantityStep of [
    "1",
    "1E-1000",
    "+.1",
    "1.",
    "0.0000000000000000000000000000000001",
    "123456789012345678901234567890.12345678901234567890",
  ]) {
    assert.deepEqual(
      validateInventorySettings({ ...defaults, quantityStep }, uoms),
      {},
    );
  }
  for (const quantityStep of [
    "",
    "0",
    "0E999",
    "-1",
    "NaN",
    "Infinity",
    "1,5",
    "abc",
    "1e",
    "1e1.5",
  ]) {
    assert.ok(
      validateInventorySettings({ ...defaults, quantityStep }, uoms)
        .quantityStep,
      quantityStep,
    );
  }
});

test("coupled tracking, unit, step and expiration rules match Domain", () => {
  for (const trackingMode of ["SERIAL", "LOT_AND_SERIAL"] as const) {
    for (const quantityStep of ["1", "1.00", "10e-1", ".01E2", "0.00100e3"]) {
      assert.deepEqual(
        validateInventorySettings(
          {
            ...defaults,
            trackingMode,
            quantityStep,
            expirationMode: "REQUIRED",
          },
          uoms,
        ),
        {},
      );
    }
    const invalid = validateInventorySettings(
      {
        ...defaults,
        trackingMode,
        baseUom: "KG",
        quantityStep: "1.00000000000000000000000001",
      },
      uoms,
    );
    assert.ok(invalid.baseUom);
    assert.ok(invalid.quantityStep);
  }
  assert.ok(
    validateInventorySettings({ ...defaults, expirationMode: "REQUIRED" }, uoms)
      .expirationMode,
  );
  assert.deepEqual(
    validateInventorySettings(
      { ...defaults, expirationMode: "OPTIONAL" },
      uoms,
    ),
    {},
  );
  assert.ok(
    validateInventorySettings({ ...defaults, baseUom: "UNKNOWN" }, uoms)
      .baseUom,
  );
});

test("editor navigation preserves origin parameters and rejects external destinations", () => {
  const origin = "/catalog/items/root?locale=ru&variant=child&tab=variants#sku";
  assert.deepEqual(inventoryItemEditLocation("inventory-id", origin), {
    name: "inventory-item-edit",
    params: { inventoryItemId: "inventory-id" },
    query: { returnTo: origin },
  });
  assert.equal(inventoryItemReturnPath(origin), origin);
  assert.equal(
    inventoryItemReturnPath("/inventory/items?search=sku&page=2&limit=20"),
    "/inventory/items?search=sku&page=2&limit=20",
  );
  for (const origin of [
    "https://outside.test",
    "//outside.test",
    "/inventory/items\\evil",
    undefined,
  ])
    assert.equal(inventoryItemReturnPath(origin), "/inventory/items");
});
