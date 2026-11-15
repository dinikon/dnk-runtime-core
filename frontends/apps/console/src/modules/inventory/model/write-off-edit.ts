import type {
  WriteOffDocument,
  WriteOffEditValues,
  WriteOffDraftLine,
  WriteOffErrors,
} from "./write-off.types.ts";
import {
  normalizeWriteOffQuantity,
  validateWriteOffDraft,
} from "./write-off-draft.ts";
export function writeOffEditValues(
  document: WriteOffDocument,
): WriteOffEditValues {
  return {
    expectedVersion: document.version,
    reason: document.reason,
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
export function copyWriteOffEdit(
  values: WriteOffEditValues,
): WriteOffEditValues {
  return {
    expectedVersion: values.expectedVersion,
    reason: values.reason,
    lines: values.lines.map((line) => ({ ...line })),
  };
}
export function writeOffEditSignature(values: WriteOffEditValues): string {
  return JSON.stringify({
    expectedVersion: values.expectedVersion,
    reason: values.reason,
    lines: values.lines.map((line) => ({
      id: line.id,
      inventoryItemId: line.id ? undefined : line.inventoryItemId,
      quantity: normalizeWriteOffQuantity(line.quantity),
      uom: line.uom,
    })),
  });
}
export function validateWriteOffEdit(
  values: WriteOffEditValues,
): WriteOffErrors {
  return validateWriteOffDraft({
    warehouseId: "selected",
    warehouseName: "",
    ownerId: "selected",
    ownerName: "",
    reason: values.reason,
    lines: values.lines,
  });
}
export function replaceWriteOffLine(
  values: WriteOffEditValues,
  key: string,
  value: WriteOffDraftLine,
): WriteOffEditValues {
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
export function newestWriteOff(
  current: WriteOffDocument | undefined,
  incoming: WriteOffDocument,
): WriteOffDocument {
  return current && current.version > incoming.version ? current : incoming;
}
