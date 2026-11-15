import type {
  StatusChangeDocument,
  StatusChangeEditValues,
  StatusChangeDraftLine,
  StatusChangeErrors,
} from "./status-change.types.ts";
import {
  normalizeStatusChangeQuantity,
  validateStatusChangeDraft,
} from "./status-change-draft.ts";
export function statusChangeEditValues(
  document: StatusChangeDocument,
): StatusChangeEditValues {
  return {
    expectedVersion: document.version,
    reason: document.reason,
    targetStatus: document.targetStatus,
    lines: document.lines.map((line) => ({
      key: line.id,
      id: line.id,
      inventoryItemId: line.inventoryItemId,
      sku: line.sku,
      baseUom: line.baseUom,
      quantity: line.sourceQuantity,
      uom: line.sourceUom,
    })),
  };
}
export function copyStatusChangeEdit(
  values: StatusChangeEditValues,
): StatusChangeEditValues {
  return {
    expectedVersion: values.expectedVersion,
    reason: values.reason,
    targetStatus: values.targetStatus,
    lines: values.lines.map((line) => ({ ...line })),
  };
}
export function statusChangeEditSignature(
  values: StatusChangeEditValues,
): string {
  return JSON.stringify({
    expectedVersion: values.expectedVersion,
    reason: values.reason,
    targetStatus: values.targetStatus,
    lines: values.lines.map((line) => ({
      id: line.id,
      inventoryItemId: line.id ? undefined : line.inventoryItemId,
      quantity: normalizeStatusChangeQuantity(line.quantity),
      uom: line.uom,
    })),
  });
}
export function validateStatusChangeEdit(
  values: StatusChangeEditValues,
): StatusChangeErrors {
  return validateStatusChangeDraft({
    warehouseId: "selected",
    warehouseName: "",
    ownerId: "selected",
    ownerName: "",
    reason: values.reason,
    targetStatus: values.targetStatus,
    lines: values.lines,
  });
}
export function replaceStatusChangeLine(
  values: StatusChangeEditValues,
  key: string,
  value: StatusChangeDraftLine,
): StatusChangeEditValues {
  return {
    ...values,
    lines: values.lines.map((line) =>
      line.key === key
        ? {
            ...value,
            id: line.id,
            inventoryItemId: line.id
              ? line.inventoryItemId
              : value.inventoryItemId,
            sku: line.id ? line.sku : value.sku,
            baseUom: line.id ? line.baseUom : value.baseUom,
          }
        : line,
    ),
  };
}
export function newestStatusChange(
  current: StatusChangeDocument | undefined,
  incoming: StatusChangeDocument,
): StatusChangeDocument {
  return current && current.version > incoming.version ? current : incoming;
}
