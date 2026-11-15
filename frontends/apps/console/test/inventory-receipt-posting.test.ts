import assert from "node:assert/strict";
import test from "node:test";
import {
  prepareIntake,
  copyIntake,
  duplicateIntakeRow,
  chooseIntakeReference,
  validateIntake,
  ReceiptIntakeAttempt,
  selectedIntakeRows,
  selectIntakeLine,
  rebaseIntake,
  intakeGroups,
  intakeBaseTotal,
  intakeDecimal,
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
      position: 0,
      plannedQuantity: "1234567890.1234567890123456789",
      executedQuantity: "0",
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

test("partial selection preserves excluded allocations and excludes their costs from the payload", () => {
  let values = prepareIntake(
    {
      ...context,
      lines: [
        context.lines[0]!,
        { ...context.lines[0]!, documentLineId: "other", position: 1 },
      ],
    },
    (() => {
      let n = 0;
      return () => String(++n);
    })(),
  );
  values.rows[0]!.quantity = "40";
  values.rows[0]!.costKnown = true;
  values.rows[0]!.costAmount = "40";
  values.rows[0]!.costCurrency = "USD";
  values = selectIntakeLine(values, "line", false);
  assert.equal(values.rows[0]!.quantity, "40");
  assert.equal(selectedIntakeRows(values).length, 1);
  assert.equal(intakeToDto(values).lines[0]!.document_line_id, "other");
  assert.deepEqual(intakeToDto(values).costs, []);
  values = selectIntakeLine(values, "line", true);
  assert.equal(values.rows[0]!.quantity, "40");
  assert.equal(intakeToDto(values).costs[0]!.amount, "40");
  values = selectIntakeLine(
    selectIntakeLine(values, "line", false),
    "other",
    false,
  );
  assert.match(validateIntake(values).form!, /от 1 до 500/);
});
test("allocations are checked per plan line even for equal SKU, using exact decimals", () => {
  const line = {
    ...context.lines[0]!,
    plannedQuantity: "1",
    remainingQuantity: "0.2999999999999999999",
    executedQuantity: "0.7000000000000000001",
  };
  const values = prepareIntake(
    {
      ...context,
      lines: [
        line,
        {
          ...line,
          documentLineId: "other",
          position: 1,
          remainingQuantity: "100",
          plannedQuantity: "100",
          executedQuantity: "0",
        },
      ],
    },
    (() => {
      let n = 0;
      return () => String(++n);
    })(),
  );
  values.rows[0]!.quantity = "0.1";
  values.rows.push({
    ...duplicateIntakeRow(values.rows[0]!, "split"),
    quantity: "0.2",
  });
  assert.equal(intakeBaseTotal([values.rows[0]!, values.rows[2]!]), "0.3");
  assert.match(validateIntake(values).lines!.line!, /Распределено 0.3/);
  assert.equal(validateIntake(values).lines!.other, undefined);
  values.rows[2]!.quantity = "0.1999999999999999999";
  assert.equal(validateIntake(values).lines, undefined);
  values.rows[2]!.uom = "G";
  assert.equal(intakeBaseTotal([values.rows[0]!, values.rows[2]!]), null);
  assert.equal(validateIntake(values).lines, undefined);
});
test("accepting the current version preserves typed input, keys and costs and revalidates remaining", () => {
  const values = prepareIntake(context, () => "stable");
  values.rows[0]!.quantity = "50";
  values.rows[0]!.costKnown = true;
  values.rows[0]!.costAmount = "0";
  values.rows[0]!.costCurrency = "USD";
  const current = {
    ...context,
    version: 4,
    status: "PARTIALLY_EXECUTED",
    lines: [
      { ...context.lines[0]!, executedQuantity: "60", remainingQuantity: "40" },
    ],
  };
  assert.equal(
    intakeGroups(values, current)[0]!.current!.remainingQuantity,
    "40",
  );
  const next = rebaseIntake(values, current);
  assert.equal(next.expectedVersion, 4);
  assert.equal(next.rows[0]!.quantity, "50");
  assert.equal(next.rows[0]!.key, "stable");
  assert.equal(next.rows[0]!.costAmount, "0");
  assert.equal(values.expectedVersion, 3);
  assert.match(validateIntake(next).lines!.line!, /осталось 40/);
  const completed = rebaseIntake(values, {
    ...current,
    status: "COMPLETED",
    lines: [{ ...current.lines[0]!, remainingQuantity: "0" }],
  });
  assert.equal(completed.rows[0]!.quantity, "50");
  assert.equal(completed.rows[0]!.selected, false);
  assert.equal(
    selectIntakeLine(completed, "line", true).rows[0]!.selected,
    false,
  );
});
test("server exponential Decimal notation expands without floating point quantity conversion", () => {
  assert.equal(intakeDecimal("1.25E-19"), "0.000000000000000000125");
  assert.equal(intakeDecimal("1.25E+3"), "1250");
  assert.equal(
    intakeDecimal("12345678901234567890.001"),
    "12345678901234567890.001",
  );
});

test("allocation removal keeps plan groups in document order", () => {
  const values = prepareIntake(
    {
      ...context,
      lines: [
        context.lines[0]!,
        { ...context.lines[0]!, documentLineId: "other", position: 1 },
      ],
    },
    (() => {
      let n = 0;
      return () => String(++n);
    })(),
  );
  values.rows.push(duplicateIntakeRow(values.rows[0]!, "split"));
  values.rows.shift();
  assert.deepEqual(
    intakeGroups(values).map((group) => group.line.documentLineId),
    ["line", "other"],
  );
});
