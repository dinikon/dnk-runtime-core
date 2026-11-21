export interface StatusTransitionsResponseDTO {
  items: { source_status: string; target_statuses: string[] }[];
}
export interface StatusChangePreviewResponseDTO {
  document_id: string;
  version: number;
  reason: string;
  target_status: string;
  positions: {
    id: string | null;
    exists: boolean;
    role: "SOURCE" | "DESTINATION";
    inventory_item_id: string;
    sku: string;
    location_id: string;
    location_code: string;
    stock_status: string;
    lot_number: string | null;
    serial_number: string | null;
    base_uom: string;
    before_quantity: string;
    delta: string;
    after_quantity: string;
  }[];
}
