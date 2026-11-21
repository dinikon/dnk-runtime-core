import type {
  InternalMoveDocument,
  InternalMoveEditValues,
  InternalMoveDraftLine,
  InternalMoveErrors,
} from "./internal-move.types.ts";
import {
  normalizeInternalMoveQuantity,
  validateInternalMoveDraft,
} from "./internal-move-draft.ts";
export function internalMoveEditValues(
  document: InternalMoveDocument,
): InternalMoveEditValues {
  return {
    expectedVersion: document.version,
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
export function copyInternalMoveEdit(
  values: InternalMoveEditValues,
): InternalMoveEditValues {
  return {
    expectedVersion: values.expectedVersion,
    lines: values.lines.map((line) => ({ ...line })),
  };
}
export function internalMoveEditSignature(
  values: InternalMoveEditValues,
): string {
  return JSON.stringify({
    expectedVersion: values.expectedVersion,
    lines: values.lines.map((line) => ({
      id: line.id,
      inventoryItemId: line.id ? undefined : line.inventoryItemId,
      quantity: normalizeInternalMoveQuantity(line.quantity),
      uom: line.uom,
    })),
  });
}
export function validateInternalMoveEdit(
  values: InternalMoveEditValues,
): InternalMoveErrors {
  return validateInternalMoveDraft({
    warehouseId: "selected",
    warehouseName: "",
    ownerId: "selected",
    ownerName: "",
    lines: values.lines,
  });
}
export function replaceInternalMoveLine(
  values: InternalMoveEditValues,
  key: string,
  value: InternalMoveDraftLine,
): InternalMoveEditValues {
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
export function newestInternalMove(
  current: InternalMoveDocument | undefined,
  incoming: InternalMoveDocument,
): InternalMoveDocument {
  return current && current.version > incoming.version ? current : incoming;
}
