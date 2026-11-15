export interface PrepareReturnLineResponseDTO {
  position: number;
  planned_quantity: string;
  executed_quantity: string;
  document_line_id: string;
  origin_execution_line_id: string;
  original_quantity: string;
  returned_quantity: string;
  returnable_quantity: string;
  inventory_item_id: string;
  sku: string;
  base_uom: string;
  current_base_uom: string;
  remaining_quantity: string;
  quantity_step: string;
  tracking_mode: "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
  expiration_mode: "NONE" | "OPTIONAL" | "REQUIRED";
}
export interface PrepareReturnResponseDTO {
  document_id: string;
  version: number;
  status: string;
  warehouse_id: string;
  reason: string;
  direction: string;
  origin_execution_id: string;
  lines: PrepareReturnLineResponseDTO[];
}
export interface ListReturnExecutionLineResponseDTO {
  document_line_id: string;
  position: number;
  sku: string;
  base_uom: string;
  quantity: string;
  allocation_count: number;
}
export interface ListReturnExecutionItemResponseDTO {
  execution_id: string;
  posting_id: string;
  posted_at: string;
  document_version_after: number;
  document_status: string;
  reason: string;
  direction: string;
  origin_execution_id: string;
  line_count: number;
  lines: ListReturnExecutionLineResponseDTO[];
}
export interface ListReturnExecutionsResponseDTO {
  items: ListReturnExecutionItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface PostReturnRequestDTO {
  expected_version: number;
  lines: {
    client_line_id: string;
    document_line_id: string;
    source_position_id?: string;
    location_id?: string;
    stock_status?: string;
    quantity: string;
    uom: string;
  }[];
}
export interface PostReturnLineResponseDTO {
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
}
export interface PostReturnPositionResponseDTO {
  id: string;
  base_uom: string;
  before_quantity: string;
  delta: string;
  after_quantity: string;
  before_version: number;
  after_version: number;
}
export interface PostReturnEntryResponseDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
}
export interface PostReturnResponseDTO {
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
  direction: string;
  origin_execution_id: string;
  posted_at: string;
  lines: PostReturnLineResponseDTO[];
  positions: PostReturnPositionResponseDTO[];
  ledger: PostReturnEntryResponseDTO[];
}
export interface ReturnSourceResponseDTO {
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
export interface ListReturnSourcesResponseDTO {
  items: ReturnSourceResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}

export interface ListReturnDestinationsResponseDTO {
  items: { id: string; code: string; name: string }[];
  total: number;
  offset: number;
  limit: number;
}
