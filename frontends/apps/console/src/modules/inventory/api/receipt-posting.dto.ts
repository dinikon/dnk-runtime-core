export interface PostReceiptLineResponseDTO {
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
export interface PostReceiptPositionResponseDTO {
  id: string;
  base_uom: string;
  before_quantity: string;
  delta: string;
  after_quantity: string;
  before_version: number;
  after_version: number;
}
export interface PostReceiptEntryResponseDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
}
export interface PostReceiptAllocationResponseDTO {
  execution_line_id: string;
  amount: string;
}
export interface PostReceiptCostResponseDTO {
  id: string;
  amount: string;
  currency: string;
  basis_kind: string;
  source_system: string | null;
  source_reference: string | null;
  allocations: PostReceiptAllocationResponseDTO[];
}
export interface PostReceiptResponseDTO {
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
  lines: PostReceiptLineResponseDTO[];
  positions: PostReceiptPositionResponseDTO[];
  ledger: PostReceiptEntryResponseDTO[];
  costs: PostReceiptCostResponseDTO[];
}
export interface GetStockExecutionLineResponseDTO {
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
export interface GetStockExecutionPositionResponseDTO {
  id: string;
  base_uom: string;
  before_quantity: string;
  delta: string;
  after_quantity: string;
  before_version: number;
  after_version: number;
}
export interface GetStockExecutionEntryResponseDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
}
export interface GetStockExecutionAllocationResponseDTO {
  execution_line_id: string;
  amount: string;
}
export interface GetStockExecutionCostResponseDTO {
  id: string;
  amount: string;
  currency: string;
  basis_kind: string;
  source_system: string | null;
  source_reference: string | null;
  allocations: GetStockExecutionAllocationResponseDTO[];
}
export interface GetStockExecutionResponseDTO {
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
  lines: GetStockExecutionLineResponseDTO[];
  positions: GetStockExecutionPositionResponseDTO[];
  ledger: GetStockExecutionEntryResponseDTO[];
  costs: GetStockExecutionCostResponseDTO[];
}
export interface GetStockPostingLineResponseDTO {
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
export interface GetStockPostingPositionResponseDTO {
  id: string;
  base_uom: string;
  before_quantity: string;
  delta: string;
  after_quantity: string;
  before_version: number;
  after_version: number;
}
export interface GetStockPostingEntryResponseDTO {
  id: string;
  position_id: string;
  quantity_delta: string;
  base_uom: string;
}
export interface GetStockPostingAllocationResponseDTO {
  execution_line_id: string;
  amount: string;
}
export interface GetStockPostingCostResponseDTO {
  id: string;
  amount: string;
  currency: string;
  basis_kind: string;
  source_system: string | null;
  source_reference: string | null;
  allocations: GetStockPostingAllocationResponseDTO[];
}
export interface GetStockPostingResponseDTO {
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
  lines: GetStockPostingLineResponseDTO[];
  positions: GetStockPostingPositionResponseDTO[];
  ledger: GetStockPostingEntryResponseDTO[];
  costs: GetStockPostingCostResponseDTO[];
}

export interface PostReceiptRequestDTO {
  expected_version: number;
  lines: {
    client_line_id: string;
    document_line_id: string;
    quantity: string;
    uom: string;
    location_id: string;
    lot_id: string | null;
    serial_id: string | null;
    stock_status: string;
  }[];
  costs: {
    amount: string;
    currency: string;
    basis_kind: "MANUAL";
    source_system: null;
    source_reference: string | null;
    allocations: { client_line_id: string; amount: string }[];
  }[];
}
export interface PrepareReceiptLineResponseDTO {
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
export interface PrepareReceiptResponseDTO {
  document_id: string;
  version: number;
  status: string;
  warehouse_id: string;
  default_storage_location_id: string | null;
  lines: PrepareReceiptLineResponseDTO[];
}
export interface ReceiptReferenceResponseDTO {
  id: string;
  label: string;
  lot_id: string | null;
  lot_number: string | null;
  manufactured_on: string | null;
  expires_on: string | null;
}
export interface ListReceiptReferencesResponseDTO {
  items: ReceiptReferenceResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface ListReceiptExecutionItemResponseDTO {
  execution_id: string;
  posting_id: string;
  posted_at: string;
  document_version_after: number;
  document_status: string;
  line_count: number;
}
export interface ListReceiptExecutionsResponseDTO {
  items: ListReceiptExecutionItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
