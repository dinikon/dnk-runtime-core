import assert from "node:assert/strict";
import test from "node:test";
import {
  prepareIssueExecution,
  copyIssueExecution,
  splitIssueAllocation,
  rebaseIssueExecution,
  validateIssueExecution,
  IssueExecutionAttempt,
} from "../src/modules/inventory/model/issue-execution.ts";
import { issueExecutionToDto } from "../src/modules/inventory/api/issue-posting.mapper.ts";
import type {
  IssuePreparation,
  IssueSource,
} from "../src/modules/inventory/model/issue-posting.types.ts";
const context: IssuePreparation = {
  documentId: "d",
  version: 3,
  status: "CONFIRMED",
  warehouseId: "w",
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
const source: IssueSource = {
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
test("issue binds a source ID and excludes hidden allocations without client-supplied dimensions", () => {
  const values = prepareIssueExecution(
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
  assert.deepEqual(validateIssueExecution(values), { rows: {}, lines: {} });
  assert.deepEqual(issueExecutionToDto(values), {
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
  const values = prepareIssueExecution(
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
  const errors = validateIssueExecution(values);
  assert.match(errors.rows["1"]!, /Недостаточно/);
  assert.match(errors.rows["2"]!, /Недостаточно/);
  values.rows[1]!.quantity = "0.1999999999999999999";
  assert.deepEqual(validateIssueExecution(values), { rows: {}, lines: {} });
  values.rows[1]!.quantity = "200";
  values.rows[1]!.uom = "G";
  assert.deepEqual(validateIssueExecution(values), { rows: {}, lines: {} });
});
test("document rebasing retains user allocations and rechecks remaining plan", () => {
  const values = prepareIssueExecution(context, () => "stable");
  values.rows[0]!.quantity = "50";
  values.rows[0]!.source = { ...source };
  const next = rebaseIssueExecution(values, {
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
    validateIssueExecution(next).lines.line!,
    /осталось по плану 40/,
  );
  assert.equal(values.expectedVersion, 3);
});
test("an unknown result retries the original source, quantity and key", () => {
  const values = prepareIssueExecution(context, () => "stable");
  values.rows[0]!.source = { ...source };
  values.rows[0]!.quantity = "30";
  const attempt = new IssueExecutionAttempt();
  const sent = attempt.begin(values, () => "first");
  sent.values.rows[0]!.source!.id = "changed-copy";
  attempt.fail(true);
  assert.equal(attempt.begin(values, () => "second").key, "first");
  assert.equal(
    attempt.begin(values, () => "second").values.rows[0]!.source!.id,
    "p",
  );
  const changed = copyIssueExecution(values);
  changed.rows[0]!.quantity = "20";
  assert.throws(() => attempt.begin(changed, () => "second"));
  attempt.fail(false);
  assert.equal(attempt.begin(changed, () => "second").key, "second");
});
test("a new serial allocation requires another source and one PCS", () => {
  const values = prepareIssueExecution(
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
  const split = splitIssueAllocation(values.rows[0]!, "r2");
  assert.equal(split.quantity, "1");
  assert.equal(split.source, null);
  values.rows.push(split);
  assert.match(validateIssueExecution(values).rows.r2!, /исходную позицию/);
});
