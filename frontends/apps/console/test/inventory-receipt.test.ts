import test from "node:test";
import assert from "node:assert/strict";
import {
  emptyReceiptDraft,
  newReceiptLine,
  ReceiptCreationAttempt,
  validateReceiptDraft,
  hasReceiptErrors,
  copyReceiptDraft,
} from "../src/modules/inventory/model/receipt-draft.ts";
import { createReceiptToDto } from "../src/modules/inventory/api/receipt.mapper.ts";
import {
  parseReceiptPage,
  receiptPageQuery,
} from "../src/modules/inventory/model/receipt-page-state.ts";
const values = {
  ...emptyReceiptDraft(),
  warehouseId: "w",
  warehouseName: "Warehouse",
  ownerId: "o",
  ownerName: "Owner",
  lines: [
    {
      ...newReceiptLine("row-1"),
      inventoryItemId: "item",
      sku: "oil",
      baseUom: "KG",
      quantity: "1234567890,1234567890123456789",
      uom: "KG",
    },
  ],
};
test("receipt keeps Decimal as text and excludes server-owned fields from payload", () => {
  const dto = createReceiptToDto(values);
  assert.equal(dto.lines[0].quantity, "1234567890.1234567890123456789");
  assert.deepEqual(Object.keys(dto).sort(), [
    "lines",
    "owner_id",
    "warehouse_id",
  ]);
  assert.equal("sku" in dto.lines[0], false);
  assert.equal("key" in dto.lines[0], false);
});
test("empty plan and duplicate SKU rows are allowed; nonpositive quantities are rejected", () => {
  assert.equal(
    hasReceiptErrors(validateReceiptDraft({ ...values, lines: [] })),
    false,
  );
  assert.equal(
    hasReceiptErrors(
      validateReceiptDraft({
        ...values,
        lines: [values.lines[0], { ...values.lines[0], key: "row-2" }],
      }),
    ),
    false,
  );
  assert.ok(
    validateReceiptDraft({
      ...values,
      lines: [{ ...values.lines[0], quantity: "0" }],
    }).lineFields["row-1"].quantity,
  );
  assert.ok(
    validateReceiptDraft({
      ...values,
      lines: [{ ...values.lines[0], quantity: "NaN" }],
    }).lineFields["row-1"].quantity,
  );
});
test("known retry keeps key; actual edits start a new attempt", () => {
  let n = 0;
  const a = new ReceiptCreationAttempt(),
    uuid = () => String(++n);
  assert.equal(a.begin(values, uuid).key, "1");
  a.fail(false);
  assert.equal(a.begin(copyReceiptDraft(values), uuid).key, "1");
  const changed = { ...values, ownerId: "other" };
  assert.equal(a.begin(changed, uuid).key, "2");
});
test("ambiguous response retries original snapshot; changed payload is blocked until resolved", () => {
  const a = new ReceiptCreationAttempt();
  a.begin(values, () => "same");
  a.fail(true);
  const sent = a.begin(values, () => "wrong");
  assert.equal(sent.key, "same");
  sent.values.lines[0].quantity = "999";
  assert.equal(
    a.begin(values, () => "wrong").values.lines[0].quantity,
    values.lines[0].quantity,
  );
  assert.throws(() => a.begin({ ...values, ownerId: "other" }, () => "new"));
  a.clear();
  assert.equal(
    a.begin({ ...values, ownerId: "other" }, () => "new").key,
    "new",
  );
});
test("local row keys may change after a known failure without changing server identity", () => {
  const a = new ReceiptCreationAttempt();
  a.begin(values, () => "same");
  a.fail(false);
  const changed = {
    ...values,
    lines: [{ ...values.lines[0], key: "replacement" }],
  };
  const next = a.begin(changed, () => "new");
  assert.equal(next.key, "same");
  assert.equal(next.values.lines[0].key, "replacement");
});
test("receipt URL round-trips filters, timezone-aware bounds and pagination", () => {
  const p = parseReceiptPage({
    search: "oil",
    owner_id: "o",
    warehouse_id: "w",
    status: "ALL",
    created_from: "2026-11-15T00:00:00Z",
    created_to: "2026-11-16T00:00:00Z",
    offset: "20",
  });
  assert.equal(p.offset, 20);
  assert.deepEqual(parseReceiptPage(receiptPageQuery(p)), p);
  assert.equal(parseReceiptPage({}).status, "DRAFT");
});
