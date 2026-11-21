import assert from "node:assert/strict";
import test from "node:test";
import {
  inventoryItemFromDto,
  inventoryItemsPageFromDto,
  inventoryItemsParamsToDto,
} from "../src/modules/inventory/api/inventory-item.mapper.ts";
import type { InventoryItemListRowDTO } from "../src/modules/inventory/api/inventory-item.dto.ts";
import {
  InventoryItemsRequestError,
  retryInventoryItems,
} from "../src/modules/inventory/model/inventory-item.errors.ts";
import {
  inventoryExpirationLabels,
  inventoryTrackingLabels,
} from "../src/modules/inventory/model/inventory-item.constants.ts";

test("inventory mapper keeps exact Decimal, identifiers and note semantics", () => {
  const dto: InventoryItemListRowDTO = {
    id: "item-1",
    sku: "000abc",
    base_uom: "KG",
    quantity_rules: { step: "0.000000000000000000000000000123456789" },
    tracking_mode: "LOT_AND_SERIAL",
    expiration_mode: "OPTIONAL",
  };
  const row = inventoryItemFromDto(dto);
  assert.deepEqual(row, {
    id: "item-1",
    sku: "000abc",
    baseUom: "KG",
    quantityStep: dto.quantity_rules.step,
    trackingMode: "LOT_AND_SERIAL",
    expirationMode: "OPTIONAL",
  });
  assert.equal(typeof row.quantityStep, "string");
  assert.equal(
    inventoryItemFromDto({ ...dto, quantity_rules: { step: "1E-50" } })
      .quantityStep,
    "1E-50",
  );
  assert.equal(
    inventoryExpirationLabels[row.expirationMode],
    "Необязательная заметка",
  );
  assert.equal(
    inventoryTrackingLabels[row.trackingMode],
    "По партиям и сериям",
  );
});

test("inventory page mapping preserves total independently of an empty page", () => {
  assert.deepEqual(
    inventoryItemsPageFromDto({ items: [], total: 73, offset: 100, limit: 50 }),
    {
      items: [],
      total: 73,
      offset: 100,
      limit: 50,
    },
  );
  assert.deepEqual(
    inventoryItemsParamsToDto({ search: "", offset: 0, limit: 50 }),
    { search: undefined, offset: 0, limit: 50 },
  );
  assert.deepEqual(
    inventoryItemsParamsToDto({ search: "Straße%_", offset: 20, limit: 20 }),
    { search: "Straße%_", offset: 20, limit: 20 },
  );
});

test("inventory retries transient reads once and never automatically retries access errors", () => {
  for (const status of [401, 403, 404, 422])
    assert.equal(
      retryInventoryItems(0, new InventoryItemsRequestError("denied", status)),
      false,
    );
  assert.equal(
    retryInventoryItems(0, new InventoryItemsRequestError("network", null)),
    true,
  );
  assert.equal(
    retryInventoryItems(0, new InventoryItemsRequestError("server", 503)),
    true,
  );
  assert.equal(retryInventoryItems(1, new Error("network")), false);
});
