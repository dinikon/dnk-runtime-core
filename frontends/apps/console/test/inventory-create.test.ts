import assert from "node:assert/strict";
import test from "node:test";
import {
  inventoryItemCreateToDto,
  inventoryItemCreatedFromDto,
} from "../src/modules/inventory/api/inventory-item-create.mapper.ts";
import { InventoryItemCreateError } from "../src/modules/inventory/model/inventory-item-create.errors.ts";
import { inventoryItemKeys } from "../src/modules/inventory/model/inventory-item.query-keys.ts";

test("create sends only the manual SKU and reads all defaults from the server", () => {
  assert.deepEqual(inventoryItemCreateToDto({ sku: "  Manual-SKU  " }), {
    sku: "Manual-SKU",
  });
  const result = inventoryItemCreatedFromDto({
    id: "server-id",
    sku: "manual-sku",
    base_uom: "L",
    quantity_rules: { step: "1.2345678901234567890123456789E-50" },
    tracking_mode: "LOT",
    expiration_mode: "OPTIONAL",
    barcodes: [],
  });
  assert.deepEqual(result, {
    id: "server-id",
    sku: "manual-sku",
    baseUom: "L",
    quantityStep: "1.2345678901234567890123456789E-50",
    trackingMode: "LOT",
    expirationMode: "OPTIONAL",
    barcodes: [],
  });
});

test("create distinguishes a definite rejection from an unconfirmed write", () => {
  for (const status of [403, 409, 422])
    assert.equal(
      new InventoryItemCreateError("rejected", status).uncertain,
      false,
    );
  for (const status of [null, 500, 502, 504])
    assert.equal(
      new InventoryItemCreateError("unconfirmed", status).uncertain,
      true,
    );
});

test("create mutation cache belongs to its exact tenant, user and session", () => {
  const key = inventoryItemKeys.create(["tenant-a", "user-a", "1"]);
  for (const scope of [
    ["tenant-b", "user-a", "1"],
    ["tenant-a", "user-b", "1"],
    ["tenant-a", "user-a", "2"],
  ] as const)
    assert.notDeepEqual(inventoryItemKeys.create(scope), key);
});
