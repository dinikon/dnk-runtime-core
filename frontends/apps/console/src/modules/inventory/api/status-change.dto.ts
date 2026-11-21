import type { StatusChangeStatus } from "../model/status-change.types";
export interface CreateStatusChangeDraftLineResponseDTO {
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
}
export interface CreateStatusChangeDraftResponseDTO {
  id: string;
  operation_type: "STATUS_CHANGE";
  status: StatusChangeStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  target_status: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: CreateStatusChangeDraftLineResponseDTO[];
}
export interface GetStatusChangeDocumentLineResponseDTO {
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
}
export interface GetStatusChangeDocumentResponseDTO {
  id: string;
  operation_type: "STATUS_CHANGE";
  status: StatusChangeStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  target_status: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: GetStatusChangeDocumentLineResponseDTO[];
}
export interface StatusChangeListItemResponseDTO {
  id: string;
  operation_type: "STATUS_CHANGE";
  status: StatusChangeStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  target_status: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  line_count: number;
}
export interface ListStatusChangeDocumentsResponseDTO {
  items: StatusChangeListItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface CreateStatusChangeDraftRequestDTO {
  warehouse_id: string;
  owner_id: string;
  reason: string;
  target_status: string;
  lines: { inventory_item_id: string; quantity: string; uom: string }[];
}

export interface PatchStatusChangeDocumentLineResponseDTO {
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
}
export interface PatchStatusChangeDocumentResponseDTO {
  id: string;
  operation_type: "STATUS_CHANGE";
  status: StatusChangeStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  target_status: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: PatchStatusChangeDocumentLineResponseDTO[];
}

export interface ConfirmStatusChangeDocumentLineResponseDTO {
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
}
export interface ConfirmStatusChangeDocumentResponseDTO {
  id: string;
  operation_type: "STATUS_CHANGE";
  status: StatusChangeStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  target_status: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: ConfirmStatusChangeDocumentLineResponseDTO[];
}

export interface CancelStatusChangeDocumentLineResponseDTO {
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
}
export interface CancelStatusChangeDocumentResponseDTO {
  id: string;
  operation_type: "STATUS_CHANGE";
  status: StatusChangeStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  target_status: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: CancelStatusChangeDocumentLineResponseDTO[];
}

export interface PatchStatusChangeDocumentRequestDTO {
  expected_version: number;
  reason?: string;
  target_status?: string;
  lines?: (
    | { id: string; quantity: string; uom: string }
    | { inventory_item_id: string; quantity: string; uom: string }
  )[];
}
export interface ConfirmStatusChangeDocumentRequestDTO {
  expected_version: number;
}
export interface CancelStatusChangeDocumentRequestDTO {
  expected_version: number;
}
