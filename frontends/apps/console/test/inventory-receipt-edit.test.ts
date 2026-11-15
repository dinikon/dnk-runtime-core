import assert from "node:assert/strict";
import test from "node:test";
import {
  receiptEditValues,
  copyReceiptEdit,
  receiptEditSignature,
  replaceReceiptLine,
  newestReceipt,
} from "../src/modules/inventory/model/receipt-edit.ts";
import { patchReceiptToDto } from "../src/modules/inventory/api/receipt.mapper.ts";
import type { ReceiptDocument } from "../src/modules/inventory/model/receipt.types.ts";
const document: ReceiptDocument = {
  id: "d",
  operationType: "RECEIPT",
  status: "DRAFT",
  warehouseId: "w",
  warehouseCode: "W",
  warehouseName: "Warehouse",
  ownerId: "o",
  ownerName: "Owner",
  sourceSystem: null,
  sourceReference: null,
  sourceVersion: null,
  createdAt: "2026-11-15T00:00:00Z",
  updatedAt: "2026-11-15T00:00:00Z",
  version: 7,
  lines: [
    {
      id: "line",
      position: 0,
      inventoryItemId: "item",
      sku: "historical",
      baseUom: "KG",
      plannedQty: "1.25",
      sourceQuantity: "1250",
      sourceUom: "G",
      factorToBase: "0.001",
      executedQty: "0",
    },
  ],
};
test("receipt editor starts with original quantity and unit, retaining server identity and baseline version", () => {
  const values = receiptEditValues(document);
  assert.equal(values.expectedVersion, 7);
  assert.equal(values.lines[0].quantity, "1250");
  assert.equal(values.lines[0].uom, "G");
  assert.equal(values.lines[0].id, "line");
  const copy = copyReceiptEdit(values);
  copy.lines[0].quantity = "1234567890.1234567890123456789";
  assert.equal(values.lines[0].quantity, "1250");
  assert.equal(values.expectedVersion, 7);
  assert.notEqual(receiptEditSignature(values), receiptEditSignature(copy));
});
test("saved lines cannot change SKU through the draft helper and payload never sends their SKU settings", () => {
  const values = receiptEditValues(document),
    line = values.lines[0];
  const edited = replaceReceiptLine(values, line.key, {
    ...line,
    id: "forged",
    inventoryItemId: "other",
    sku: "renamed",
    baseUom: "L",
    quantity: "1500,125",
  });
  assert.equal(edited.lines[0].id, "line");
  assert.equal(edited.lines[0].sku, "historical");
  assert.equal(edited.lines[0].baseUom, "KG");
  edited.lines.push({
    key: "local",
    inventoryItemId: "new",
    sku: "NEW",
    baseUom: "KG",
    quantity: "1234567890.1234567890123456789",
    uom: "KG",
  });
  assert.deepEqual(patchReceiptToDto(edited), {
    expected_version: 7,
    lines: [
      { id: "line", quantity: "1500.125", uom: "G" },
      {
        inventory_item_id: "new",
        quantity: "1234567890.1234567890123456789",
        uom: "KG",
      },
    ],
  });
});
test("late mutation or creation snapshots cannot lower a cached document version", () => {
  const confirmed = { ...document, version: 8, status: "CONFIRMED" as const };
  assert.equal(newestReceipt(confirmed, document), confirmed);
  assert.equal(newestReceipt(document, confirmed), confirmed);
  assert.equal(newestReceipt(undefined, confirmed), confirmed);
});
