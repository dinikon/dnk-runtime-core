import type {
  ReturnDocument,
  ReturnEditValues,
  ReturnDraftLine,
  ReturnErrors,
} from "./return.types.ts";
import { normalizeReturnQuantity, validateReturnPlan } from "./return-draft.ts";
export function returnEditValues(document: ReturnDocument): ReturnEditValues {
  return {
    expectedVersion: document.version,
    reason: document.reason,
    lines: document.lines.map((line) => ({
      key: line.id,
      id: line.id,
      originExecutionLineId: line.originExecutionLineId,
      inventoryItemId: line.inventoryItemId,
      sku: line.sku,
      baseUom: line.baseUom,
      quantity: line.sourceQuantity,
      uom: line.sourceUom,
    })),
  };
}
export function copyReturnEdit(values: ReturnEditValues): ReturnEditValues {
  return {
    expectedVersion: values.expectedVersion,
    reason: values.reason,
    lines: values.lines.map((line) => ({ ...line })),
  };
}
export function returnEditSignature(values: ReturnEditValues): string {
  return JSON.stringify({
    expectedVersion: values.expectedVersion,
    reason: values.reason,
    lines: values.lines.map((line) => ({
      id: line.id,
      originExecutionLineId: line.originExecutionLineId,
      quantity: normalizeReturnQuantity(line.quantity),
      uom: line.uom,
    })),
  });
}
export function validateReturnEdit(values: ReturnEditValues): ReturnErrors {
  return validateReturnPlan({
    reason: values.reason,
    lines: values.lines,
  });
}
export function replaceReturnLine(
  values: ReturnEditValues,
  key: string,
  value: ReturnDraftLine,
): ReturnEditValues {
  return {
    ...values,
    lines: values.lines.map((line) =>
      line.key === key
        ? {
            ...value,
            id: line.id,
            originExecutionLineId: line.id
              ? line.originExecutionLineId
              : value.originExecutionLineId,
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
export function newestReturn(
  current: ReturnDocument | undefined,
  incoming: ReturnDocument,
): ReturnDocument {
  return current && current.version > incoming.version ? current : incoming;
}
