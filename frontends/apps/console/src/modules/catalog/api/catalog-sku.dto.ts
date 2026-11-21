export type SetCatalogSkuRequestDTO =
  | { mode: "existing"; inventory_item_id: string }
  | { mode: "create"; sku: string }
  | { mode: "clear" };

export interface SetCatalogSkuResponseDTO {
  item_id: string;
  inventory_item_id: string | null;
  sku: string | null;
  inventory_item_created: boolean;
}
