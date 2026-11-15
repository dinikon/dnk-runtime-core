import type { InternalMoveStatus } from "../model/internal-move.types";
export interface CreateInternalMoveDraftLineResponseDTO {
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
export interface CreateInternalMoveDraftResponseDTO {
  id: string;
  operation_type: "INTERNAL_MOVE";
  status: InternalMoveStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: CreateInternalMoveDraftLineResponseDTO[];
}
export interface GetInternalMoveDocumentLineResponseDTO {
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
export interface GetInternalMoveDocumentResponseDTO {
  id: string;
  operation_type: "INTERNAL_MOVE";
  status: InternalMoveStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: GetInternalMoveDocumentLineResponseDTO[];
}
export interface InternalMoveListItemResponseDTO {
  id: string;
  operation_type: "INTERNAL_MOVE";
  status: InternalMoveStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  line_count: number;
}
export interface ListInternalMoveDocumentsResponseDTO {
  items: InternalMoveListItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface CreateInternalMoveDraftRequestDTO {
  warehouse_id: string;
  owner_id: string;
  lines: { inventory_item_id: string; quantity: string; uom: string }[];
}

export interface PatchInternalMoveDocumentLineResponseDTO {
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
export interface PatchInternalMoveDocumentResponseDTO {
  id: string;
  operation_type: "INTERNAL_MOVE";
  status: InternalMoveStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: PatchInternalMoveDocumentLineResponseDTO[];
}

export interface ConfirmInternalMoveDocumentLineResponseDTO {
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
export interface ConfirmInternalMoveDocumentResponseDTO {
  id: string;
  operation_type: "INTERNAL_MOVE";
  status: InternalMoveStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: ConfirmInternalMoveDocumentLineResponseDTO[];
}

export interface CancelInternalMoveDocumentLineResponseDTO {
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
export interface CancelInternalMoveDocumentResponseDTO {
  id: string;
  operation_type: "INTERNAL_MOVE";
  status: InternalMoveStatus;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  owner_id: string;
  owner_name: string | null;
  source_system: string | null;
  source_reference: string | null;
  source_version: number | null;
  created_at: string;
  updated_at: string;
  version: number;
  lines: CancelInternalMoveDocumentLineResponseDTO[];
}

export interface PatchInternalMoveDocumentRequestDTO {
  expected_version: number;
  lines: (
    | { id: string; quantity: string; uom: string }
    | { inventory_item_id: string; quantity: string; uom: string }
  )[];
}
export interface ConfirmInternalMoveDocumentRequestDTO {
  expected_version: number;
}
export interface CancelInternalMoveDocumentRequestDTO {
  expected_version: number;
}
