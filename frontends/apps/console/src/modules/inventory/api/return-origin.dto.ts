export interface ReturnOriginResponseDTO {
  execution_id: string;
  document_id: string;
  operation_type: string;
  direction: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  lines: {
    id: string;
    position: number;
    inventory_item_id: string;
    sku: string;
    base_uom: string;
    quantity: string;
    returned_quantity: string;
    remaining_quantity: string;
    location_id: string;
    location_code: string;
    stock_status: string;
    lot_id: string | null;
    lot_number: string | null;
    serial_id: string | null;
    serial_number: string | null;
  }[];
}
