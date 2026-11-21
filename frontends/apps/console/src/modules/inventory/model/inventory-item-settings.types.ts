import type {
  InventoryExpirationMode,
  InventoryTrackingMode,
} from "./inventory-item.types.ts";

export interface InventoryItemSettings {
  baseUom: string;
  quantityStep: string;
  trackingMode: InventoryTrackingMode;
  expirationMode: InventoryExpirationMode;
}

export interface InventoryItemDetails extends InventoryItemSettings {
  id: string;
  sku: string;
  barcodes: { id: string; barcode: string }[];
}

export type InventoryUomDimension =
  "COUNT" | "MASS" | "VOLUME" | "LENGTH" | "AREA";
export interface InventoryUom {
  code: string;
  dimension: InventoryUomDimension;
}
export type InventorySettingsErrors = Partial<
  Record<keyof InventoryItemSettings, string>
>;
