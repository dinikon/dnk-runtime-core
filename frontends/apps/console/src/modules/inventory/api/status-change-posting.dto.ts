export interface PrepareStatusChangeLineResponseDTO {
  position: number;
  planned_quantity: string;
  executed_quantity: string;
  document_line_id: string;
  inventory_item_id: string;
  sku: string;
  base_uom: string;
  current_base_uom: string;
  remaining_quantity: string;
  quantity_step: string;
  tracking_mode: "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
  expiration_mode: "NONE" | "OPTIONAL" | "REQUIRED";
}
export interface PrepareStatusChangeResponseDTO {
  document_id: string;
  version: number;
  status: string;
  warehouse_id: string;
  reason: string;
  target_status: string;
  lines: PrepareStatusChangeLineResponseDTO[];
}
export interface ListStatusChangeExecutionLineResponseDTO {
  document_line_id: string;
  position: number;
  sku: string;
  base_uom: string;
  quantity: string;
  allocation_count: number;
}
export interface ListStatusChangeExecutionItemResponseDTO {
  execution_id: string;
  posting_id: string;
  posted_at: string;
  document_version_after: number;
  document_status: string;
  reason: string;
  target_status: string;
  line_count: number;
  lines: ListStatusChangeExecutionLineResponseDTO[];
}
export interface ListStatusChangeExecutionsResponseDTO {
  items: ListStatusChangeExecutionItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface PostStatusChangeRequestDTO {
  expected_version: number;
  lines: {
    client_line_id: string;
    document_line_id: string;
    source_position_id: string;
    quantity: string;
    uom: string;
  }[];
}
export interface PostStatusChangeLineResponseDTO {
  id: string;
  client_line_id: string;
  document_line_id: string;
  inventory_item_id: string;
  sku: string;
  base_uom: string;
  quantity: string;
  source_quantity: string;
  source_uom: string;
  factor_to_base: string;
  location_id: string;
  location_code: string;
  lot_id: string | null;
  lot_number: string | null;
  serial_id: string | null;
  serial_number: string | null;
  stock_status: string;
  position_id: string;
  ledger_entry_id: string;
  destination_stock_status: string;
  destination_position_id: string;
  destination_ledger_entry_id: string;
  destination_location_id: string;
  destination_location_code: string;
}
export interface PostStatusChangePositionResponseDTO {
  id: string;
  base_uom: string;
  before_quantity: string;
  delta: string;
  after_quantity: string;
  before_version: number;
  after_version: number;
}
export interface PostStatusChangeEntryResponseDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
}
export interface PostStatusChangeResponseDTO {
  document_id: string;
  document_version_before: number;
  document_version_after: number;
  document_status: string;
  execution_id: string;
  posting_id: string;
  event_id: string;
  actor_id: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  target_status: string;
  posted_at: string;
  lines: PostStatusChangeLineResponseDTO[];
  positions: PostStatusChangePositionResponseDTO[];
  ledger: PostStatusChangeEntryResponseDTO[];
}
export interface StatusChangeSourceResponseDTO {
  id: string;
  inventory_item_id: string;
  location_id: string;
  location_code: string;
  stock_status: string;
  lot_id: string | null;
  lot_number: string | null;
  serial_id: string | null;
  serial_number: string | null;
  manufactured_on: string | null;
  expires_on: string | null;
  base_uom: string;
  on_hand_quantity: string;
  version: number;
}
export interface ListStatusChangeSourcesResponseDTO {
  items: StatusChangeSourceResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
