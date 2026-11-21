export interface InventoryItemListRowDTO {
  id: string;
  sku: string;
  base_uom: string;
  quantity_rules: { step: string };
  tracking_mode: "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
  expiration_mode: "NONE" | "OPTIONAL" | "REQUIRED";
}

export interface ListInventoryItemsRequestDTO {
  search?: string;
  offset: number;
  limit: number;
}

export interface ListInventoryItemsResponseDTO {
  items: InventoryItemListRowDTO[];
  total: number;
  offset: number;
  limit: number;
}
