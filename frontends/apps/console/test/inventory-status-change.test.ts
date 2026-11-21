import assert from "node:assert/strict";
import test from "node:test";
import {
  prepareStatusChangeExecution,
  copyStatusChangeExecution,
  splitStatusChangeAllocation,
  rebaseStatusChangeExecution,
  validateStatusChangeExecution,
  StatusChangeExecutionAttempt,
} from "../src/modules/inventory/model/status-change-execution.ts";
import { statusChangeExecutionToDto } from "../src/modules/inventory/api/status-change-posting.mapper.ts";
import type {
  StatusChangePreparation,
  StatusChangeSource,
} from "../src/modules/inventory/model/status-change-posting.types.ts";
const context: StatusChangePreparation = {
  documentId: "d",
  version: 3,
  status: "CONFIRMED",
  warehouseId: "w",
  reason: "Повреждение товара",
  targetStatus: "QUARANTINE",
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
const source: StatusChangeSource = {
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
test("status-change binds a source ID and excludes hidden allocations without client-supplied dimensions", () => {
  const values = prepareStatusChangeExecution(
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
  assert.deepEqual(validateStatusChangeExecution(values), {
    rows: {},
    lines: {},
  });
  assert.deepEqual(statusChangeExecutionToDto(values), {
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
  const values = prepareStatusChangeExecution(
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
  const errors = validateStatusChangeExecution(values);
  assert.match(errors.rows["1"]!, /Недостаточно/);
  assert.match(errors.rows["2"]!, /Недостаточно/);
  values.rows[1]!.quantity = "0.1999999999999999999";
  assert.deepEqual(validateStatusChangeExecution(values), {
    rows: {},
    lines: {},
  });
  values.rows[1]!.quantity = "200";
  values.rows[1]!.uom = "G";
  assert.deepEqual(validateStatusChangeExecution(values), {
    rows: {},
    lines: {},
  });
});
test("document rebasing retains user allocations and rechecks remaining plan", () => {
  const values = prepareStatusChangeExecution(context, () => "stable");
  values.rows[0]!.quantity = "50";
  values.rows[0]!.source = { ...source };
  const next = rebaseStatusChangeExecution(values, {
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
    validateStatusChangeExecution(next).lines.line!,
    /осталось по плану 40/,
  );
  assert.equal(values.expectedVersion, 3);
});
test("an unknown result retries the original source, quantity and key", () => {
  const values = prepareStatusChangeExecution(context, () => "stable");
  values.rows[0]!.source = { ...source };
  values.rows[0]!.quantity = "30";
  const attempt = new StatusChangeExecutionAttempt();
  const sent = attempt.begin(values, () => "first");
  sent.values.rows[0]!.source!.id = "changed-copy";
  attempt.fail(true);
  assert.equal(attempt.begin(values, () => "second").key, "first");
  assert.equal(
    attempt.begin(values, () => "second").values.rows[0]!.source!.id,
    "p",
  );
  const changed = copyStatusChangeExecution(values);
  changed.rows[0]!.quantity = "20";
  assert.throws(() => attempt.begin(changed, () => "second"));
  attempt.fail(false);
  assert.equal(attempt.begin(changed, () => "second").key, "second");
});
test("a new serial allocation requires another source and one PCS", () => {
  const values = prepareStatusChangeExecution(
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
  const split = splitStatusChangeAllocation(values.rows[0]!, "r2");
  assert.equal(split.quantity, "1");
  assert.equal(split.source, null);
  values.rows.push(split);
  assert.match(
    validateStatusChangeExecution(values).rows.r2!,
    /исходную позицию/,
  );
});

import {
  emptyStatusChangeDraft,
  validateStatusChangeDraft,
  StatusChangeCreationAttempt,
  hasStatusChangeErrors,
} from "../src/modules/inventory/model/status-change-draft.ts";
import { createStatusChangeToDto } from "../src/modules/inventory/api/status-change.mapper.ts";
import { accountingTarget } from "../src/modules/inventory/model/stock-accounting-navigation.ts";
test("status-change draft requires a reason and preserves canonical text in its own payload", () => {
  const draft = emptyStatusChangeDraft();
  draft.warehouseId = "w";
  draft.ownerId = "owner";
  assert.equal(hasStatusChangeErrors(validateStatusChangeDraft(draft)), true);
  assert.match(validateStatusChangeDraft(draft).reason!, /причину/);
  draft.reason = "  Порча\nпри хранении  ";
  draft.targetStatus = "QUARANTINE";
  assert.equal(hasStatusChangeErrors(validateStatusChangeDraft(draft)), false);
  assert.equal(createStatusChangeToDto(draft).reason, "Порча\nпри хранении");
});
test("an uncertain status-change creation freezes its reason as well as quantities", () => {
  const draft = emptyStatusChangeDraft();
  draft.reason = "Повреждение";
  const attempt = new StatusChangeCreationAttempt();
  const first = attempt.begin(draft, () => "key");
  attempt.fail(true);
  first.values.reason = "changed-copy";
  assert.equal(
    attempt.begin(draft, () => "other").values.reason,
    "Повреждение",
  );
  const changed = { ...draft, targetStatus: "BLOCKED" };
  assert.throws(() => attempt.begin(changed, () => "other"));
  attempt.fail(false);
  assert.equal(attempt.begin(changed, () => "other").key, "other");
});
test("STATUS_CHANGE navigation stays distinct from ISSUE and receipt", () => {
  assert.equal(
    accountingTarget({
      kind: "document",
      id: "d",
      operationType: "STATUS_CHANGE",
    }).name,
    "inventory-status-change-document",
  );
  assert.equal(
    accountingTarget({ kind: "document", id: "d", operationType: "ISSUE" })
      .name,
    "inventory-issue-document",
  );
});

import {
  statusChangePreviewFromDto,
  statusTransitionsFromDto,
} from "../src/modules/inventory/api/status-change-preview.mapper.ts";
import {
  statusChangeEditSignature,
  statusChangeEditValues,
} from "../src/modules/inventory/model/status-change-edit.ts";
import type { StatusChangeDocument } from "../src/modules/inventory/model/status-change.types.ts";
test("preview keeps decimal strings, nullable identity and both sides", () => {
  const p = statusChangePreviewFromDto({
    document_id: "d",
    version: 3,
    reason: "Контроль",
    target_status: "BLOCKED",
    positions: [
      {
        id: null,
        exists: false,
        role: "DESTINATION",
        inventory_item_id: "i",
        sku: "sku",
        location_id: "l",
        location_code: "A1",
        stock_status: "BLOCKED",
        lot_number: "000Lot",
        serial_number: "000Sn",
        base_uom: "KG",
        before_quantity: "0",
        delta: "0.1234567890123456789",
        after_quantity: "0.1234567890123456789",
      },
    ],
  });
  assert.equal(p.positions[0]!.id, null);
  assert.equal(p.positions[0]!.exists, false);
  assert.equal(p.positions[0]!.after, "0.1234567890123456789");
  assert.equal(p.positions[0]!.serialNumber, "000Sn");
});
test("transition adapter preserves server matrix instead of inferring targets", () => {
  assert.deepEqual(
    statusTransitionsFromDto({
      items: [{ source_status: "DAMAGED", target_statuses: ["BLOCKED"] }],
    }),
    [{ sourceStatus: "DAMAGED", targetStatuses: ["BLOCKED"] }],
  );
});
test("target participates in draft/edit signatures and outgoing contracts", () => {
  const draft = emptyStatusChangeDraft();
  draft.targetStatus = "BLOCKED";
  draft.reason = "Контроль";
  assert.equal(createStatusChangeToDto(draft).target_status, "BLOCKED");
  const d: StatusChangeDocument = {
    id: "d",
    operationType: "STATUS_CHANGE",
    status: "DRAFT",
    warehouseId: "w",
    warehouseCode: "W",
    warehouseName: "Склад",
    ownerId: "o",
    ownerName: null,
    reason: "Контроль",
    targetStatus: "BLOCKED",
    sourceSystem: null,
    sourceReference: null,
    sourceVersion: null,
    createdAt: "",
    updatedAt: "",
    version: 3,
    lines: [],
  };
  const edit = statusChangeEditValues(d);
  assert.equal(edit.targetStatus, "BLOCKED");
  assert.notEqual(
    statusChangeEditSignature(edit),
    statusChangeEditSignature({ ...edit, targetStatus: "DAMAGED" }),
  );
});
