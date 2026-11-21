export interface PrepareInternalMoveLineResponseDTO {
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
export interface PrepareInternalMoveResponseDTO {
  document_id: string;
  version: number;
  status: string;
  warehouse_id: string;
  lines: PrepareInternalMoveLineResponseDTO[];
}
export interface ListInternalMoveExecutionLineResponseDTO {
  document_line_id: string;
  position: number;
  sku: string;
  base_uom: string;
  quantity: string;
  allocation_count: number;
}
export interface ListInternalMoveExecutionItemResponseDTO {
  execution_id: string;
  posting_id: string;
  posted_at: string;
  document_version_after: number;
  document_status: string;
  line_count: number;
  lines: ListInternalMoveExecutionLineResponseDTO[];
}
export interface ListInternalMoveExecutionsResponseDTO {
  items: ListInternalMoveExecutionItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface PostInternalMoveRequestDTO {
  expected_version: number;
  lines: {
    client_line_id: string;
    document_line_id: string;
    source_position_id: string;
    destination_location_id: string;
    quantity: string;
    uom: string;
  }[];
}
export interface PostInternalMoveLineResponseDTO {
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
  destination_location_id: string;
  destination_location_code: string;
  lot_id: string | null;
  lot_number: string | null;
  serial_id: string | null;
  serial_number: string | null;
  stock_status: string;
  position_id: string;
  ledger_entry_id: string;
  destination_position_id: string;
  destination_ledger_entry_id: string;
}
export interface PostInternalMovePositionResponseDTO {
  id: string;
  base_uom: string;
  before_quantity: string;
  delta: string;
  after_quantity: string;
  before_version: number;
  after_version: number;
}
export interface PostInternalMoveEntryResponseDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
}
export interface PostInternalMoveResponseDTO {
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
  posted_at: string;
  lines: PostInternalMoveLineResponseDTO[];
  positions: PostInternalMovePositionResponseDTO[];
  ledger: PostInternalMoveEntryResponseDTO[];
}
export interface InternalMoveSourceResponseDTO {
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
export interface ListInternalMoveSourcesResponseDTO {
  items: InternalMoveSourceResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}

export interface ListInternalMoveDestinationsResponseDTO {
  items: { id: string; code: string; name: string }[];
  total: number;
  offset: number;
  limit: number;
}
