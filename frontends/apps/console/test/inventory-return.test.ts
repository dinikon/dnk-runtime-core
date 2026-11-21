import assert from "node:assert/strict";
import test from "node:test";
import {
  prepareReturnExecution,
  copyReturnExecution,
  validateReturnExecution,
  ReturnExecutionAttempt,
  rebaseReturnExecution,
} from "../src/modules/inventory/model/return-execution.ts";
import { returnExecutionToDto } from "../src/modules/inventory/api/return-posting.mapper.ts";
import type {
  ReturnPreparation,
  ReturnSource,
} from "../src/modules/inventory/model/return-posting.types.ts";
import {
  parseReturnPage,
  returnPageQuery,
} from "../src/modules/inventory/model/return-page-state.ts";
import {
  emptyReturnDraft,
  ReturnCreationAttempt,
} from "../src/modules/inventory/model/return-draft.ts";
import { createReturnToDto } from "../src/modules/inventory/api/return.mapper.ts";
import { accountingTarget } from "../src/modules/inventory/model/stock-accounting-navigation.ts";
const context: ReturnPreparation = {
  documentId: "d",
  version: 3,
  status: "CONFIRMED",
  warehouseId: "w",
  reason: "Возврат",
  direction: "FROM_RECIPIENT",
  originExecutionId: "origin",
  lines: [
    {
      documentLineId: "line",
      originExecutionLineId: "actual-line",
      originalQuantity: "100",
      returnedQuantity: "20",
      returnableQuantity: "80",
      position: 0,
      inventoryItemId: "i",
      sku: "SKU",
      baseUom: "KG",
      currentBaseUom: "KG",
      plannedQuantity: "90",
      executedQuantity: "0",
      remainingQuantity: "90",
      quantityStep: "0.0000000000000000001",
      trackingMode: "NONE",
      expirationMode: "NONE",
    },
  ],
};
const source: ReturnSource = {
  id: "p",
  inventoryItemId: "i",
  locationId: "l",
  locationCode: "A1",
  stockStatus: "SELLABLE",
  lotId: null,
  lotNumber: null,
  serialId: null,
  serialNumber: null,
  manufacturedOn: null,
  expiresOn: null,
  baseUom: "KG",
  onHandQuantity: "50",
  version: 1,
};
test("incoming return requires explicit address and state and never sends editable identity", () => {
  const values = prepareReturnExecution(context, () => "r");
  const row = values.rows[0]!;
  row.quantity = "30";
  assert.match(validateReturnExecution(values).rows.r!, /адрес и состояние/);
  row.destination = { id: "dest", code: "B", name: "Приёмка" };
  row.stockStatus = "QUARANTINE";
  assert.deepEqual(validateReturnExecution(values), { rows: {}, lines: {} });
  assert.deepEqual(returnExecutionToDto(values), {
    expected_version: 3,
    lines: [
      {
        client_line_id: "r",
        document_line_id: "line",
        location_id: "dest",
        stock_status: "QUARANTINE",
        quantity: "30",
        uom: "KG",
      },
    ],
  });
  row.source = { ...source };
  assert.equal(
    "source_position_id" in returnExecutionToDto(values).lines[0]!,
    false,
  );
});
test("outgoing return sends a concrete position and checks physical quantity independently", () => {
  const values = prepareReturnExecution(
    { ...context, direction: "TO_SUPPLIER" },
    () => "r",
  );
  const row = values.rows[0]!;
  row.source = { ...source };
  row.quantity = "51";
  assert.match(
    validateReturnExecution(values).rows.r!,
    /Недостаточно физического/,
  );
  row.quantity = "50";
  assert.deepEqual(validateReturnExecution(values), { rows: {}, lines: {} });
  assert.deepEqual(returnExecutionToDto(values), {
    expected_version: 3,
    lines: [
      {
        client_line_id: "r",
        document_line_id: "line",
        source_position_id: "p",
        quantity: "50",
        uom: "KG",
      },
    ],
  });
});
test("origin limit aggregates different plan lines with exact decimals", () => {
  let n = 0;
  const values = prepareReturnExecution(
    {
      ...context,
      lines: [
        context.lines[0]!,
        { ...context.lines[0]!, documentLineId: "other" },
      ],
    },
    () => String(++n),
  );
  for (const row of values.rows) {
    row.destination = { id: "dest", code: "B", name: "Приёмка" };
    row.stockStatus = "SELLABLE";
    row.returnableQuantity = "0.2999999999999999999";
    row.quantity = row.key === "1" ? "0.1" : "0.2";
  }
  assert.match(
    validateReturnExecution(values).rows["1"]!,
    /остаток к возврату/,
  );
  assert.match(
    validateReturnExecution(values).rows["2"]!,
    /остаток к возврату/,
  );
  values.rows[1]!.quantity = "0.1999999999999999999";
  assert.deepEqual(validateReturnExecution(values), { rows: {}, lines: {} });
});
test("unknown posting freezes key, destination and state while preserving the draft", () => {
  const values = prepareReturnExecution(context, () => "r");
  values.rows[0]!.destination = { id: "dest", code: "B", name: "Приёмка" };
  values.rows[0]!.stockStatus = "QUARANTINE";
  values.rows[0]!.quantity = "30";
  const attempt = new ReturnExecutionAttempt();
  const first = attempt.begin(values, () => "key");
  attempt.fail(true);
  first.values.rows[0]!.destination!.id = "changed-copy";
  assert.equal(attempt.begin(values, () => "new").key, "key");
  assert.equal(
    attempt.begin(values, () => "new").values.rows[0]!.destination!.id,
    "dest",
  );
  const changed = copyReturnExecution(values);
  changed.rows[0]!.stockStatus = "SELLABLE";
  assert.throws(() => attempt.begin(changed, () => "new"));
  attempt.fail(false);
  assert.equal(attempt.begin(changed, () => "new").key, "new");
});
test("rebase refreshes both original and plan limits without losing entered quantity", () => {
  const values = prepareReturnExecution(context, () => "r");
  values.rows[0]!.quantity = "30";
  values.rows[0]!.destination = { id: "dest", code: "B", name: "Приёмка" };
  values.rows[0]!.stockStatus = "BLOCKED";
  const next = rebaseReturnExecution(values, {
    ...context,
    version: 4,
    lines: [
      {
        ...context.lines[0]!,
        returnableQuantity: "20",
        returnedQuantity: "80",
        remainingQuantity: "25",
      },
    ],
  });
  assert.equal(next.rows[0]!.quantity, "30");
  assert.equal(next.rows[0]!.destination!.id, "dest");
  assert.equal(next.rows[0]!.stockStatus, "BLOCKED");
  assert.equal(next.expectedVersion, 4);
  assert.match(validateReturnExecution(next).rows.r!, /остаток к возврату/);
  assert.ok(validateReturnExecution(next).lines.line);
});
test("creation retries freeze the original execution and line IDs", () => {
  const values = emptyReturnDraft();
  values.originExecutionId = "origin";
  values.reason = "  Возврат  ";
  values.lines = [
    {
      key: "r",
      originExecutionLineId: "actual",
      inventoryItemId: "i",
      sku: "SKU",
      baseUom: "KG",
      quantity: "1,05",
      uom: "KG",
    },
  ];
  assert.deepEqual(createReturnToDto(values), {
    origin_execution_id: "origin",
    reason: "Возврат",
    lines: [
      { origin_execution_line_id: "actual", quantity: "1.05", uom: "KG" },
    ],
  });
  const attempt = new ReturnCreationAttempt();
  attempt.begin(values, () => "first");
  attempt.fail(true);
  assert.throws(() =>
    attempt.begin({ ...values, originExecutionId: "other" }, () => "new"),
  );
  assert.equal(attempt.begin(values, () => "new").key, "first");
});
test("source list filter survives URL roundtrip and accounting navigation points to RETURN", () => {
  const p = parseReturnPage({ origin_execution_id: "origin", status: "ALL" });
  assert.equal(p.originExecutionId, "origin");
  assert.equal(returnPageQuery(p).origin_execution_id, "origin");
  assert.equal(
    accountingTarget({ kind: "document", id: "d", operationType: "RETURN" })
      .name,
    "inventory-return-document",
  );
});

import { returnKeys } from "../src/modules/inventory/model/return.query-keys.ts";
import { returnPostingKeys } from "../src/modules/inventory/model/return-posting.query-keys.ts";
import { validateReturnEdit } from "../src/modules/inventory/model/return-edit.ts";
test("return caches isolate tenant/user/session and snapshot all candidate parameters", () => {
  const scope = ["tenant", "user", "session"] as const;
  const params = { documentLineId: "line", search: "000Lot", offset: 20 };
  const key = returnPostingKeys.sources(scope, "d", params);
  params.search = "changed";
  assert.equal(key[7].search, "000Lot");
  assert.notDeepEqual(
    returnPostingKeys.context(scope, "d"),
    returnPostingKeys.context(["other", "user", "session"], "d"),
  );
  assert.notDeepEqual(
    returnKeys.origin(scope, "origin"),
    returnKeys.origin(["tenant", "other", "session"], "origin"),
  );
  assert.notDeepEqual(
    returnKeys.origin(scope, "origin"),
    returnKeys.origin(["tenant", "user", "other"], "origin"),
  );
  assert.notDeepEqual(
    returnPostingKeys.destinations(scope, "d", { search: "A", offset: 0 }),
    returnPostingKeys.destinations(scope, "d", { search: "A", offset: 20 }),
  );
});
test("draft editing validates its own fields without supplying a fabricated origin ID", () => {
  assert.deepEqual(
    validateReturnEdit({ expectedVersion: 2, reason: "Причина", lines: [] }),
    { lineFields: {} },
  );
});
