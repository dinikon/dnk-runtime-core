import assert from "node:assert/strict";
import test from "node:test";
import {
  prepareIntake,
  copyIntake,
  duplicateIntakeRow,
  chooseIntakeReference,
  validateIntake,
  ReceiptIntakeAttempt,
} from "../src/modules/inventory/model/receipt-intake.ts";
import { intakeToDto } from "../src/modules/inventory/api/receipt-posting.mapper.ts";
import type { ReceiptPreparation } from "../src/modules/inventory/model/receipt-posting.types.ts";
const context: ReceiptPreparation = {
  documentId: "d",
  version: 3,
  status: "CONFIRMED",
  warehouseId: "w",
  defaultStorageLocationId: "location",
  lines: [
    {
      documentLineId: "line",
      inventoryItemId: "item",
      sku: "SKU",
      baseUom: "KG",
      currentBaseUom: "KG",
      remainingQuantity: "1234567890.1234567890123456789",
      quantityStep: "0.0000000000000000001",
      trackingMode: "NONE",
      expirationMode: "NONE",
    },
  ],
};
test("receipt prefill and payload preserve exact decimal strings; unknown cost differs from zero", () => {
  const values = prepareIntake(context, () => "row");
  assert.equal(values.rows[0].quantity, context.lines[0].remainingQuantity);
  assert.deepEqual(intakeToDto(values).costs, []);
  values.rows[0].costKnown = true;
  values.rows[0].costAmount = "0";
  values.rows[0].costCurrency = "usd";
  const payload = intakeToDto(values);
  assert.equal(payload.lines[0].quantity, context.lines[0].remainingQuantity);
  assert.equal(payload.costs[0].amount, "0");
  assert.deepEqual(payload.costs[0].allocations, [
    { client_line_id: "row", amount: "0" },
  ]);
  values.unallocatedCost = {
    known: true,
    amount: "25,0001",
    currency: "USD",
    reference: "invoice",
  };
  assert.deepEqual(intakeToDto(values).costs[1].allocations, []);
  assert.equal(intakeToDto(values).costs[1].amount, "25.0001");
});
test("uncertain receipt retries immutable original input with same key; edits require a new attempt", () => {
  const values = prepareIntake(context, () => "row"),
    attempt = new ReceiptIntakeAttempt();
  const sent = attempt.begin(values, () => "first");
  sent.values.rows[0].quantity = "999";
  attempt.fail(true);
  assert.equal(
    attempt.begin(values, () => "second").values.rows[0].quantity,
    values.rows[0].quantity,
  );
  assert.equal(attempt.begin(values, () => "second").key, "first");
  const changed = copyIntake(values);
  changed.rows[0].quantity = "2";
  assert.throws(() => attempt.begin(changed, () => "second"));
  attempt.fail(false);
  assert.equal(attempt.begin(changed, () => "second").key, "second");
  attempt.clear();
  assert.equal(attempt.begin(values, () => "third").key, "third");
});
test("serial prefill, duplication and lot selection retain traceability; dates only come from lot", () => {
  const values = prepareIntake(
    {
      ...context,
      lines: [
        {
          ...context.lines[0],
          baseUom: "PCS",
          currentBaseUom: "PCS",
          trackingMode: "LOT_AND_SERIAL",
          expirationMode: "REQUIRED",
        },
      ],
    },
    () => "r",
  );
  assert.equal(values.rows[0].quantity, "1");
  const selected = chooseIntakeReference(values.rows[0], "serials", {
    id: "s",
    label: "000Sn",
    lotId: "lot",
    lotNumber: "000Lot",
    manufacturedOn: "2026-01-01",
    expiresOn: "2028-01-01",
  });
  values.rows = [selected];
  assert.deepEqual(validateIntake(values), { rows: {} });
  const duplicate = duplicateIntakeRow(selected, "r2");
  assert.equal(duplicate.serialId, "");
  assert.equal(duplicate.lotId, "lot");
  values.rows.push({ ...selected, key: "duplicate" });
  assert.match(validateIntake(values).rows.duplicate!, /уже выбран/);
  const changedLot = chooseIntakeReference(selected, "lots", {
    id: "other",
    label: "L2",
    lotId: null,
    lotNumber: null,
    manufacturedOn: null,
    expiresOn: null,
  });
  assert.equal(changedLot.serialId, "");
  assert.equal(changedLot.expiresOn, null);
});
