import { validateInventorySettings } from "./inventory-item-settings.validation.ts";
import type { InventoryUom } from "./inventory-item-settings.types.ts";
import type {
  InventoryItemEditErrors,
  InventoryItemEditValues,
} from "./inventory-item-editor.types.ts";
import { InventoryItemWriteError } from "./inventory-item-write.errors.ts";
export function emptyInventoryItemErrors(): InventoryItemEditErrors {
  return { fields: {}, barcodeRows: {} };
}
export function validateInventoryItemEditor(
  value: InventoryItemEditValues,
  uoms: readonly InventoryUom[],
  settingsChanged: boolean,
): InventoryItemEditErrors {
  const errors = emptyInventoryItemErrors();
  if (settingsChanged) errors.fields = validateInventorySettings(value, uoms);
  if (!value.sku.trim()) errors.fields.sku = "Укажите код SKU.";
  const codes = new Map<string, string[]>();
  for (const row of value.barcodes) {
    const code = row.barcode.trim();
    if (!code)
      errors.barcodeRows[row.key] = "Укажите штрихкод или удалите строку.";
    else codes.set(code, [...(codes.get(code) ?? []), row.key]);
  }
  for (const keys of codes.values())
    if (keys.length > 1)
      for (const key of keys)
        errors.barcodeRows[key] = "Этот штрихкод повторяется в карточке.";
  return errors;
}
export function inventoryItemErrorsForSnapshot(
  error: InventoryItemWriteError,
  sent: InventoryItemEditValues,
  current: InventoryItemEditValues,
): InventoryItemEditErrors {
  const result = emptyInventoryItemErrors();
  for (const field of [
    "sku",
    "baseUom",
    "quantityStep",
    "trackingMode",
    "expirationMode",
  ] as const)
    if (current[field] === sent[field] && error.fields[field])
      result.fields[field] = error.fields[field];
  for (const [index, message] of Object.entries(error.barcodeIssues)) {
    const row = sent.barcodes[Number(index)];
    if (
      row &&
      current.barcodes.some(
        (value) => value.key === row.key && value.barcode === row.barcode,
      )
    )
      result.barcodeRows[row.key] = message;
  }
  if (
    error.fields.barcodes &&
    current.barcodes.length === sent.barcodes.length &&
    current.barcodes.every(
      (row, index) =>
        row.key === sent.barcodes[index]?.key &&
        row.barcode === sent.barcodes[index]?.barcode,
    )
  )
    result.fields.barcodes = error.fields.barcodes;
  return result;
}
