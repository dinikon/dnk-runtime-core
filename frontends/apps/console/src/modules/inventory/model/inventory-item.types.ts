export type InventoryTrackingMode =
  "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
export type InventoryExpirationMode = "NONE" | "OPTIONAL" | "REQUIRED";

export interface InventoryItemListRow {
  id: string;
  sku: string;
  baseUom: string;
  quantityStep: string;
  trackingMode: InventoryTrackingMode;
  expirationMode: InventoryExpirationMode;
}

export interface InventoryItemsPage {
  items: InventoryItemListRow[];
  total: number;
  offset: number;
  limit: number;
}

export interface InventoryItemsListParams {
  search: string;
  offset: number;
  limit: number;
}

export interface InventoryItemsPageParams {
  search: string;
  page: number;
  limit: number;
}
