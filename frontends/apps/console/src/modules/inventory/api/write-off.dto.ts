import type { WriteOffStatus } from "../model/write-off.types";
export interface CreateWriteOffDraftLineResponseDTO {
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
export interface CreateWriteOffDraftResponseDTO {
  id: string;
  operation_type: "WRITE_OFF";
  status: WriteOffStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: CreateWriteOffDraftLineResponseDTO[];
}
export interface GetWriteOffDocumentLineResponseDTO {
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
export interface GetWriteOffDocumentResponseDTO {
  id: string;
  operation_type: "WRITE_OFF";
  status: WriteOffStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: GetWriteOffDocumentLineResponseDTO[];
}
export interface WriteOffListItemResponseDTO {
  id: string;
  operation_type: "WRITE_OFF";
  status: WriteOffStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  line_count: number;
}
export interface ListWriteOffDocumentsResponseDTO {
  items: WriteOffListItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface CreateWriteOffDraftRequestDTO {
  warehouse_id: string;
  owner_id: string;
  reason: string;
  lines: { inventory_item_id: string; quantity: string; uom: string }[];
}

export interface PatchWriteOffDocumentLineResponseDTO {
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
export interface PatchWriteOffDocumentResponseDTO {
  id: string;
  operation_type: "WRITE_OFF";
  status: WriteOffStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: PatchWriteOffDocumentLineResponseDTO[];
}

export interface ConfirmWriteOffDocumentLineResponseDTO {
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
export interface ConfirmWriteOffDocumentResponseDTO {
  id: string;
  operation_type: "WRITE_OFF";
  status: WriteOffStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: ConfirmWriteOffDocumentLineResponseDTO[];
}

export interface CancelWriteOffDocumentLineResponseDTO {
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
export interface CancelWriteOffDocumentResponseDTO {
  id: string;
  operation_type: "WRITE_OFF";
  status: WriteOffStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  reason: string;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: CancelWriteOffDocumentLineResponseDTO[];
}

export interface PatchWriteOffDocumentRequestDTO {
  expected_version: number;
  reason?: string;
  lines?: (
    | { id: string; quantity: string; uom: string }
    | { inventory_item_id: string; quantity: string; uom: string }
  )[];
}
export interface ConfirmWriteOffDocumentRequestDTO {
  expected_version: number;
}
export interface CancelWriteOffDocumentRequestDTO {
  expected_version: number;
}
