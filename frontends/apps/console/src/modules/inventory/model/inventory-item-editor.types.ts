import type { InventoryItemSettings } from "./inventory-item-settings.types.ts";
import type { InventoryScope } from "./inventory-scope.types.ts";
export interface InventoryBarcodeInput {
  key: string;
  barcode: string;
}
export interface InventoryItemEditValues extends InventoryItemSettings {
  sku: string;
  barcodes: InventoryBarcodeInput[];
}
export type InventoryItemChanges = Partial<
  InventoryItemSettings & { sku: string; barcodes: string[] }
>;
export interface InventoryItemEditErrors {
  fields: Partial<Record<keyof InventoryItemChanges, string>>;
  barcodeRows: Record<string, string>;
}
export interface InventoryItemMutationInput {
  id: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export interface InventoryItemDeleteTarget {
  id: string;
  sku: string;
}
