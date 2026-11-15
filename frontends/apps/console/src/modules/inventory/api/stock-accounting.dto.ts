export interface ListStockPositionsItemDTO {
  id: string;
  inventory_item_id: string;
  sku: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_is_active: boolean;
  location_id: string;
  location_code: string;
  location_name: string;
  location_is_active: boolean;
  owner_id: string;
  owner_name: string | null;
  lot_id: string | null;
  lot_number: string | null;
  serial_id: string | null;
  serial_number: string | null;
  stock_status: string;
  base_uom: string;
  manufactured_on: string | null;
  expires_on: string | null;
  on_hand_qty: string;
  version: number;
}
export interface ListStockPositionsResultDTO {
  items: ListStockPositionsItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface GetStockPositionResultDTO {
  id: string;
  inventory_item_id: string;
  sku: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_is_active: boolean;
  location_id: string;
  location_code: string;
  location_name: string;
  location_is_active: boolean;
  owner_id: string;
  owner_name: string | null;
  lot_id: string | null;
  lot_number: string | null;
  serial_id: string | null;
  serial_number: string | null;
  stock_status: string;
  base_uom: string;
  manufactured_on: string | null;
  expires_on: string | null;
  on_hand_qty: string;
  version: number;
  ledger_quantity: string;
}
export interface ListStockMovementsItemDTO {
  id: string;
  position_id: string;
  inventory_item_id: string;
  sku: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_is_active: boolean;
  location_id: string;
  location_code: string;
  location_name: string;
  location_is_active: boolean;
  owner_id: string;
  owner_name: string | null;
  lot_id: string | null;
  lot_number: string | null;
  serial_id: string | null;
  serial_number: string | null;
  stock_status: string;
  base_uom: string;
  manufactured_on: string | null;
  expires_on: string | null;
  document_id: string;
  execution_id: string;
  posting_id: string;
  document_status: string;
  operation_type: string;
  posted_at: string;
  quantity_delta: string;
  execution_line_ids: string[];
  historical_skus: string[];
}
export interface MovementPositionSnapshotDTO {
  id: string;
  quantity: string;
  version: number;
}
export interface ListStockMovementsResultDTO {
  items: ListStockMovementsItemDTO[];
  total: number;
  offset: number;
  limit: number;
  position: MovementPositionSnapshotDTO | null;
}
export interface ListStockExecutionsItemDTO {
  id: string;
  document_id: string;
  document_status: string;
  document_version: number;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  operation_type: string;
  executed_at: string;
  posting_id: string | null;
  line_count: number;
}
export interface ListStockExecutionsResultDTO {
  items: ListStockExecutionsItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface ListStockPostingsItemDTO {
  id: string;
  execution_id: string;
  document_id: string;
  document_status: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  operation_type: string;
  posted_at: string;
  entry_count: number;
}
export interface ListStockPostingsResultDTO {
  items: ListStockPostingsItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface GetStockExecutionDetailsLineDTO {
  id: string;
  document_line_id: string;
  inventory_item_id: string;
  sku: string;
  sku_at_document: string;
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
  ledger_entry_ids: string[];
  sku_at_receipt: string | null;
  serial_number_at_receipt: string | null;
  location_code_at_receipt: string | null;
  destination_location_id: string | null;
  destination_location_code: string | null;
  source_ledger_entry_id: string | null;
  destination_ledger_entry_id: string | null;
}
export interface GetStockExecutionDetailsEntryDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
  execution_line_ids: string[];
}
export interface GetStockExecutionDetailsAllocationDTO {
  execution_line_id: string;
  amount: string;
}
export interface GetStockExecutionDetailsCostDTO {
  id: string;
  amount: string;
  currency: string;
  basis_kind: string;
  source_system: string | null;
  source_reference: string | null;
  allocations: GetStockExecutionDetailsAllocationDTO[];
}
export interface GetStockExecutionDetailsResultDTO {
  id: string;
  execution_id: string;
  posting_id: string | null;
  document_id: string;
  document_version_at_execution: number;
  document_current_version: number;
  document_current_status: string;
  operation_type: string;
  executed_at: string;
  posted_at: string | null;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  has_receipt_result: boolean;
  lines: GetStockExecutionDetailsLineDTO[];
  ledger: GetStockExecutionDetailsEntryDTO[];
  costs: GetStockExecutionDetailsCostDTO[];
}
export interface GetStockPostingDetailsLineDTO {
  id: string;
  document_line_id: string;
  inventory_item_id: string;
  sku: string;
  sku_at_document: string;
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
  ledger_entry_ids: string[];
  sku_at_receipt: string | null;
  serial_number_at_receipt: string | null;
  location_code_at_receipt: string | null;
  destination_location_id: string | null;
  destination_location_code: string | null;
  source_ledger_entry_id: string | null;
  destination_ledger_entry_id: string | null;
}
export interface GetStockPostingDetailsEntryDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
  execution_line_ids: string[];
}
export interface GetStockPostingDetailsAllocationDTO {
  execution_line_id: string;
  amount: string;
}
export interface GetStockPostingDetailsCostDTO {
  id: string;
  amount: string;
  currency: string;
  basis_kind: string;
  source_system: string | null;
  source_reference: string | null;
  allocations: GetStockPostingDetailsAllocationDTO[];
}
export interface GetStockPostingDetailsResultDTO {
  id: string;
  execution_id: string;
  posting_id: string | null;
  document_id: string;
  document_version_at_execution: number;
  document_current_version: number;
  document_current_status: string;
  operation_type: string;
  executed_at: string;
  posted_at: string | null;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  has_receipt_result: boolean;
  lines: GetStockPostingDetailsLineDTO[];
  ledger: GetStockPostingDetailsEntryDTO[];
  costs: GetStockPostingDetailsCostDTO[];
}

export interface ListStockBalancesItemDTO {
  key: string;
  inventory_item_id: string;
  sku: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  warehouse_is_active: boolean;
  location_id: string;
  location_code: string;
  location_name: string;
  location_is_active: boolean;
  owner_id: string;
  owner_name: string | null;
  lot_id: string | null;
  lot_number: string | null;
  serial_id: string | null;
  serial_number: string | null;
  stock_status: string;
  base_uom: string;
  manufactured_on: string | null;
  expires_on: string | null;
  on_hand_qty: string;
  position_count: number;
  lot_count: number;
  serial_count: number;
}
export interface ListStockBalancesResultDTO {
  items: ListStockBalancesItemDTO[];
  total: number;
  offset: number;
  limit: number;
}
