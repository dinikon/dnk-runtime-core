export interface GetInventoryItemResponseDTO {
  id: string;
  sku: string;
  base_uom: string;
  quantity_rules: { step: string };
  tracking_mode: "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
  expiration_mode: "NONE" | "OPTIONAL" | "REQUIRED";
  barcodes: { id: string; barcode: string }[];
}

export interface PatchInventoryItemRequestDTO {
  sku?: string;
  barcodes?: string[];
  base_uom?: string;
  quantity_rules?: { step: string };
  tracking_mode?: "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
  expiration_mode?: "NONE" | "OPTIONAL" | "REQUIRED";
}

export interface PatchInventoryItemResponseDTO {
  id: string;
  sku: string;
  base_uom: string;
  quantity_rules: { step: string };
  tracking_mode: "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
  expiration_mode: "NONE" | "OPTIONAL" | "REQUIRED";
  barcodes: { id: string; barcode: string }[];
}

export interface ListInventoryUomsResponseDTO {
  items: {
    code: string;
    dimension: "COUNT" | "MASS" | "VOLUME" | "LENGTH" | "AREA";
  }[];
}
