import assert from "node:assert/strict";
import test from "node:test";
import {
  prepareWriteOffExecution,
  copyWriteOffExecution,
  splitWriteOffAllocation,
  rebaseWriteOffExecution,
  validateWriteOffExecution,
  WriteOffExecutionAttempt,
} from "../src/modules/inventory/model/write-off-execution.ts";
import { writeOffExecutionToDto } from "../src/modules/inventory/api/write-off-posting.mapper.ts";
import type {
  WriteOffPreparation,
  WriteOffSource,
} from "../src/modules/inventory/model/write-off-posting.types.ts";
const context: WriteOffPreparation = {
  documentId: "d",
  version: 3,
  status: "CONFIRMED",
  warehouseId: "w",
  reason: "Повреждение товара",
  lines: [
    {
      documentLineId: "line",
      position: 0,
      inventoryItemId: "item",
      sku: "SKU",
      baseUom: "KG",
      currentBaseUom: "KG",
      plannedQuantity: "100",
      executedQuantity: "0",
      remainingQuantity: "100",
      quantityStep: "0.0000000000000000001",
      trackingMode: "NONE",
      expirationMode: "NONE",
    },
  ],
};
const source: WriteOffSource = {
  id: "p",
  inventoryItemId: "item",
  locationId: "loc",
  locationCode: "A1",
  stockStatus: "DAMAGED",
  lotId: null,
  lotNumber: null,
  serialId: null,
  serialNumber: null,
  manufacturedOn: null,
  expiresOn: null,
  baseUom: "KG",
  onHandQuantity: "100",
  version: 1,
};
test("write-off binds a source ID and excludes hidden allocations without client-supplied dimensions", () => {
  const values = prepareWriteOffExecution(
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
  values.rows[0]!.source = { ...source };
  values.rows[0]!.quantity = "30";
  values.rows[1]!.selected = false;
  assert.deepEqual(validateWriteOffExecution(values), { rows: {}, lines: {} });
  assert.deepEqual(writeOffExecutionToDto(values), {
    expected_version: 3,
    lines: [
      {
        client_line_id: "1",
        document_line_id: "line",
        source_position_id: "p",
        quantity: "30",
        uom: "KG",
      },
    ],
  });
  assert.equal(values.rows[1]!.quantity, "100");
});
test("the source limit aggregates allocations from different plan lines with exact quantities", () => {
  const values = prepareWriteOffExecution(
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
  for (const row of values.rows) {
    row.source = { ...source, onHandQuantity: "0.2999999999999999999" };
    row.quantity = row.documentLineId === "line" ? "0.1" : "0.2";
  }
  const errors = validateWriteOffExecution(values);
  assert.match(errors.rows["1"]!, /Недостаточно/);
  assert.match(errors.rows["2"]!, /Недостаточно/);
  values.rows[1]!.quantity = "0.1999999999999999999";
  assert.deepEqual(validateWriteOffExecution(values), { rows: {}, lines: {} });
  values.rows[1]!.quantity = "200";
  values.rows[1]!.uom = "G";
  assert.deepEqual(validateWriteOffExecution(values), { rows: {}, lines: {} });
});
test("document rebasing retains user allocations and rechecks remaining plan", () => {
  const values = prepareWriteOffExecution(context, () => "stable");
  values.rows[0]!.quantity = "50";
  values.rows[0]!.source = { ...source };
  const next = rebaseWriteOffExecution(values, {
    ...context,
    version: 4,
    status: "PARTIALLY_EXECUTED",
    lines: [
      { ...context.lines[0]!, executedQuantity: "60", remainingQuantity: "40" },
    ],
  });
  assert.equal(next.expectedVersion, 4);
  assert.equal(next.rows[0]!.key, "stable");
  assert.equal(next.rows[0]!.quantity, "50");
  assert.equal(next.rows[0]!.source!.id, "p");
  assert.match(
    validateWriteOffExecution(next).lines.line!,
    /осталось по плану 40/,
  );
  assert.equal(values.expectedVersion, 3);
});
test("an unknown result retries the original source, quantity and key", () => {
  const values = prepareWriteOffExecution(context, () => "stable");
  values.rows[0]!.source = { ...source };
  values.rows[0]!.quantity = "30";
  const attempt = new WriteOffExecutionAttempt();
  const sent = attempt.begin(values, () => "first");
  sent.values.rows[0]!.source!.id = "changed-copy";
  attempt.fail(true);
  assert.equal(attempt.begin(values, () => "second").key, "first");
  assert.equal(
    attempt.begin(values, () => "second").values.rows[0]!.source!.id,
    "p",
  );
  const changed = copyWriteOffExecution(values);
  changed.rows[0]!.quantity = "20";
  assert.throws(() => attempt.begin(changed, () => "second"));
  attempt.fail(false);
  assert.equal(attempt.begin(changed, () => "second").key, "second");
});
test("a new serial allocation requires another source and one PCS", () => {
  const values = prepareWriteOffExecution(
    {
      ...context,
      lines: [
        {
          ...context.lines[0]!,
          baseUom: "PCS",
          currentBaseUom: "PCS",
          trackingMode: "LOT_AND_SERIAL",
        },
      ],
    },
    () => "r",
  );
  values.rows[0]!.source = {
    ...source,
    serialId: "s",
    lotId: "lot",
    baseUom: "PCS",
    onHandQuantity: "1",
  };
  assert.equal(values.rows[0]!.quantity, "1");
  const split = splitWriteOffAllocation(values.rows[0]!, "r2");
  assert.equal(split.quantity, "1");
  assert.equal(split.source, null);
  values.rows.push(split);
  assert.match(validateWriteOffExecution(values).rows.r2!, /исходную позицию/);
});

import {
  emptyWriteOffDraft,
  validateWriteOffDraft,
  WriteOffCreationAttempt,
  hasWriteOffErrors,
} from "../src/modules/inventory/model/write-off-draft.ts";
import { createWriteOffToDto } from "../src/modules/inventory/api/write-off.mapper.ts";
import { accountingTarget } from "../src/modules/inventory/model/stock-accounting-navigation.ts";
test("write-off draft requires a reason and preserves canonical text in its own payload", () => {
  const draft = emptyWriteOffDraft();
  draft.warehouseId = "w";
  draft.ownerId = "owner";
  assert.equal(hasWriteOffErrors(validateWriteOffDraft(draft)), true);
  assert.match(validateWriteOffDraft(draft).reason!, /причину/);
  draft.reason = "  Порча\nпри хранении  ";
  assert.equal(hasWriteOffErrors(validateWriteOffDraft(draft)), false);
  assert.equal(createWriteOffToDto(draft).reason, "Порча\nпри хранении");
});
test("an uncertain write-off creation freezes its reason as well as quantities", () => {
  const draft = emptyWriteOffDraft();
  draft.reason = "Повреждение";
  const attempt = new WriteOffCreationAttempt();
  const first = attempt.begin(draft, () => "key");
  attempt.fail(true);
  first.values.reason = "changed-copy";
  assert.equal(
    attempt.begin(draft, () => "other").values.reason,
    "Повреждение",
  );
  const changed = { ...draft, reason: "Другая причина" };
  assert.throws(() => attempt.begin(changed, () => "other"));
  attempt.fail(false);
  assert.equal(attempt.begin(changed, () => "other").key, "other");
});
test("WRITE_OFF navigation stays distinct from ISSUE and receipt", () => {
  assert.equal(
    accountingTarget({ kind: "document", id: "d", operationType: "WRITE_OFF" })
      .name,
    "inventory-write-off-document",
  );
  assert.equal(
    accountingTarget({ kind: "document", id: "d", operationType: "ISSUE" })
      .name,
    "inventory-issue-document",
  );
});
