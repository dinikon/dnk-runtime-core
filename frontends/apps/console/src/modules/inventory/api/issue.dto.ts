import type { IssueStatus } from "../model/issue.types";
export interface CreateIssueDraftLineResponseDTO {
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
export interface CreateIssueDraftResponseDTO {
  id: string;
  operation_type: "ISSUE";
  status: IssueStatus;
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
  lines: CreateIssueDraftLineResponseDTO[];
}
export interface GetIssueDocumentLineResponseDTO {
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
export interface GetIssueDocumentResponseDTO {
  id: string;
  operation_type: "ISSUE";
  status: IssueStatus;
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
  lines: GetIssueDocumentLineResponseDTO[];
}
export interface IssueListItemResponseDTO {
  id: string;
  operation_type: "ISSUE";
  status: IssueStatus;
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
export interface ListIssueDocumentsResponseDTO {
  items: IssueListItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface CreateIssueDraftRequestDTO {
  warehouse_id: string;
  owner_id: string;
  lines: { inventory_item_id: string; quantity: string; uom: string }[];
}

export interface PatchIssueDocumentLineResponseDTO {
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
export interface PatchIssueDocumentResponseDTO {
  id: string;
  operation_type: "ISSUE";
  status: IssueStatus;
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
  lines: PatchIssueDocumentLineResponseDTO[];
}

export interface ConfirmIssueDocumentLineResponseDTO {
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
export interface ConfirmIssueDocumentResponseDTO {
  id: string;
  operation_type: "ISSUE";
  status: IssueStatus;
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
  lines: ConfirmIssueDocumentLineResponseDTO[];
}

export interface CancelIssueDocumentLineResponseDTO {
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
export interface CancelIssueDocumentResponseDTO {
  id: string;
  operation_type: "ISSUE";
  status: IssueStatus;
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
  lines: CancelIssueDocumentLineResponseDTO[];
}

export interface PatchIssueDocumentRequestDTO {
  expected_version: number;
  lines: (
    | { id: string; quantity: string; uom: string }
    | { inventory_item_id: string; quantity: string; uom: string }
  )[];
}
export interface ConfirmIssueDocumentRequestDTO {
  expected_version: number;
}
export interface CancelIssueDocumentRequestDTO {
  expected_version: number;
}
