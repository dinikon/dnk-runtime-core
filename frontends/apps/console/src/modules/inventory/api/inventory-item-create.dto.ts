export interface CreateInventoryItemRequestDTO {
  sku: string;
}

export interface CreateInventoryItemResponseDTO {
  id: string;
  sku: string;
  base_uom: string;
  quantity_rules: { step: string };
  tracking_mode: "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
  expiration_mode: "NONE" | "OPTIONAL" | "REQUIRED";
  barcodes: { id: string; barcode: string }[];
}
