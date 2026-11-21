export interface GetInternalMoveExecutionLineResponseDTO {
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
export interface GetInternalMoveExecutionPositionResponseDTO {
  id: string;
  base_uom: string;
  before_quantity: string;
  delta: string;
  after_quantity: string;
  before_version: number;
  after_version: number;
}
export interface GetInternalMoveExecutionEntryResponseDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
}
export interface GetInternalMoveExecutionResultResponseDTO {
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
  lines: GetInternalMoveExecutionLineResponseDTO[];
  positions: GetInternalMoveExecutionPositionResponseDTO[];
  ledger: GetInternalMoveExecutionEntryResponseDTO[];
}
