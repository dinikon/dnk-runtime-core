import type { InventoryItemDetails } from "./inventory-item-settings.types.ts";
import type {
  InventoryBarcodeInput,
  InventoryItemChanges,
  InventoryItemEditValues,
} from "./inventory-item-editor.types.ts";
import {
  inventorySettingsFields,
  inventorySettingsSnapshot,
} from "./inventory-item-settings-draft.ts";
const scalarFields = ["sku", ...inventorySettingsFields] as const;
export function inventoryItemEditSnapshot(
  value: InventoryItemEditValues,
): InventoryItemEditValues {
  return {
    ...inventorySettingsSnapshot(value),
    sku: value.sku,
    barcodes: value.barcodes.map((row) => ({ ...row })),
  };
}
function sameBarcodes(
  left: readonly InventoryBarcodeInput[],
  right: readonly InventoryBarcodeInput[],
): boolean {
  return (
    left.length === right.length &&
    left.every((row, index) => row.barcode === right[index]?.barcode)
  );
}
export function inventoryItemChanges(
  value: InventoryItemEditValues,
  baseline: InventoryItemEditValues,
): InventoryItemChanges {
  const changes: InventoryItemChanges = {};
  if (value.sku !== baseline.sku) changes.sku = value.sku;
  if (value.baseUom !== baseline.baseUom) changes.baseUom = value.baseUom;
  if (value.quantityStep !== baseline.quantityStep)
    changes.quantityStep = value.quantityStep;
  if (value.trackingMode !== baseline.trackingMode)
    changes.trackingMode = value.trackingMode;
  if (value.expirationMode !== baseline.expirationMode)
    changes.expirationMode = value.expirationMode;
  if (!sameBarcodes(value.barcodes, baseline.barcodes))
    changes.barcodes = value.barcodes.map((row) => row.barcode);
  return changes;
}
export class InventoryItemEditorDraft {
  values: InventoryItemEditValues | null = null;
  private baseline: InventoryItemEditValues | null = null;
  private sequence = 0;
  get changes(): InventoryItemChanges {
    return this.values && this.baseline
      ? inventoryItemChanges(this.values, this.baseline)
      : {};
  }
  get dirty(): boolean {
    return Object.keys(this.changes).length > 0;
  }
  receive(item: InventoryItemDetails): void {
    if (!this.dirty) this.reset(item);
  }
  change(value: InventoryItemEditValues): void {
    this.values = inventoryItemEditSnapshot(value);
  }
  addBarcode(): void {
    if (this.values)
      this.values.barcodes.push({ key: `new:${++this.sequence}`, barcode: "" });
  }
  reset(item: InventoryItemDetails): void {
    this.values = {
      ...inventorySettingsSnapshot(item),
      sku: item.sku,
      barcodes: item.barcodes.map((row) => ({
        key: `saved:${row.id}`,
        barcode: row.barcode,
      })),
    };
    this.baseline = inventoryItemEditSnapshot(this.values);
  }
  acknowledge(
    sent: InventoryItemEditValues,
    result: InventoryItemDetails,
  ): void {
    if (!this.values) return;
    const current = inventoryItemEditSnapshot(this.values);
    this.reset(result);
    const acknowledged = this.values!;
    for (const field of scalarFields) {
      if (current[field] !== sent[field])
        Object.assign(acknowledged, { [field]: current[field] });
    }
    // Ответ заменяет коллекцию только если её отправленный снимок ещё не изменён.
    if (!sameBarcodes(current.barcodes, sent.barcodes))
      acknowledged.barcodes = current.barcodes;
  }
  rebase(result: InventoryItemDetails): void {
    const current = this.values ? inventoryItemEditSnapshot(this.values) : null;
    this.reset(result);
    if (current) this.values = current;
  }
  clear(): void {
    this.values = null;
    this.baseline = null;
  }
}
