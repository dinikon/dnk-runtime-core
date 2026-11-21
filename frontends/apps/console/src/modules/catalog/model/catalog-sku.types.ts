export type CatalogSkuSelection =
  | { mode: "existing"; inventoryItemId: string }
  | { mode: "create"; sku: string }
  | { mode: "clear" };

export interface SetCatalogSkuResult {
  itemId: string;
  inventoryItemId: string | null;
  sku: string | null;
  inventoryItemCreated: boolean;
}
