import type { ReturnStatus } from "../model/return.types";
export interface CreateReturnDraftLineResponseDTO {
  id: string;
  position: number;
  inventory_item_id: string;
  sku: string;
  base_uom: string;
  planned_qty: string;
  source_quantity: string;
  source_uom: string;
  factor_to_base: string;
  executed_qty: string;
  remaining_qty: string;
  origin_execution_line_id: string;
}
export interface CreateReturnDraftResponseDTO {
  id: string;
  operation_type: "RETURN";
  status: ReturnStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  direction: string;
  origin_execution_id: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: CreateReturnDraftLineResponseDTO[];
}
export interface GetReturnDocumentLineResponseDTO {
  id: string;
  position: number;
  inventory_item_id: string;
  sku: string;
  base_uom: string;
  planned_qty: string;
  source_quantity: string;
  source_uom: string;
  factor_to_base: string;
  executed_qty: string;
  remaining_qty: string;
  origin_execution_line_id: string;
}
export interface GetReturnDocumentResponseDTO {
  id: string;
  operation_type: "RETURN";
  status: ReturnStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  direction: string;
  origin_execution_id: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: GetReturnDocumentLineResponseDTO[];
}
export interface ReturnListItemResponseDTO {
  id: string;
  operation_type: "RETURN";
  status: ReturnStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  direction: string;
  origin_execution_id: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  line_count: number;
}
export interface ListReturnDocumentsResponseDTO {
  items: ReturnListItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface CreateReturnDraftRequestDTO {
  origin_execution_id: string;
  reason: string;
  lines: { origin_execution_line_id: string; quantity: string; uom: string }[];
}

export interface PatchReturnDocumentLineResponseDTO {
  id: string;
  position: number;
  inventory_item_id: string;
  sku: string;
  base_uom: string;
  planned_qty: string;
  source_quantity: string;
  source_uom: string;
  factor_to_base: string;
  executed_qty: string;
  remaining_qty: string;
  origin_execution_line_id: string;
}
export interface PatchReturnDocumentResponseDTO {
  id: string;
  operation_type: "RETURN";
  status: ReturnStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  direction: string;
  origin_execution_id: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: PatchReturnDocumentLineResponseDTO[];
}

export interface ConfirmReturnDocumentLineResponseDTO {
  id: string;
  position: number;
  inventory_item_id: string;
  sku: string;
  base_uom: string;
  planned_qty: string;
  source_quantity: string;
  source_uom: string;
  factor_to_base: string;
  executed_qty: string;
  remaining_qty: string;
  origin_execution_line_id: string;
}
export interface ConfirmReturnDocumentResponseDTO {
  id: string;
  operation_type: "RETURN";
  status: ReturnStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  direction: string;
  origin_execution_id: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: ConfirmReturnDocumentLineResponseDTO[];
}

export interface CancelReturnDocumentLineResponseDTO {
  id: string;
  position: number;
  inventory_item_id: string;
  sku: string;
  base_uom: string;
  planned_qty: string;
  source_quantity: string;
  source_uom: string;
  factor_to_base: string;
  executed_qty: string;
  remaining_qty: string;
  origin_execution_line_id: string;
}
export interface CancelReturnDocumentResponseDTO {
  id: string;
  operation_type: "RETURN";
  status: ReturnStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  direction: string;
  origin_execution_id: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: CancelReturnDocumentLineResponseDTO[];
}

export interface PatchReturnDocumentRequestDTO {
  expected_version: number;
  reason?: string;
  lines?: (
    | { id: string; quantity: string; uom: string }
    | { origin_execution_line_id: string; quantity: string; uom: string }
  )[];
}
export interface ConfirmReturnDocumentRequestDTO {
  expected_version: number;
}
export interface CancelReturnDocumentRequestDTO {
  expected_version: number;
}
