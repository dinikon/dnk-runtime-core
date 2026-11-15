import type {
  ReceiptDocument,
  ReceiptEditValues,
  ReceiptDraftLine,
  ReceiptErrors,
} from "./receipt.types.ts";
import {
  normalizeReceiptQuantity,
  validateReceiptDraft,
} from "./receipt-draft.ts";
export function receiptEditValues(
  document: ReceiptDocument,
): ReceiptEditValues {
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
export function copyReceiptEdit(values: ReceiptEditValues): ReceiptEditValues {
  return {
    expectedVersion: values.expectedVersion,
    lines: values.lines.map((line) => ({ ...line })),
  };
}
export function receiptEditSignature(values: ReceiptEditValues): string {
  return JSON.stringify({
    expectedVersion: values.expectedVersion,
    lines: values.lines.map((line) => ({
      id: line.id,
      inventoryItemId: line.id ? undefined : line.inventoryItemId,
      quantity: normalizeReceiptQuantity(line.quantity),
      uom: line.uom,
    })),
  });
}
export function validateReceiptEdit(values: ReceiptEditValues): ReceiptErrors {
  return validateReceiptDraft({
    warehouseId: "selected",
    warehouseName: "",
    ownerId: "selected",
    ownerName: "",
    lines: values.lines,
  });
}
export function replaceReceiptLine(
  values: ReceiptEditValues,
  key: string,
  value: ReceiptDraftLine,
): ReceiptEditValues {
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
export function newestReceipt(
  current: ReceiptDocument | undefined,
  incoming: ReceiptDocument,
): ReceiptDocument {
  return current && current.version > incoming.version ? current : incoming;
}
