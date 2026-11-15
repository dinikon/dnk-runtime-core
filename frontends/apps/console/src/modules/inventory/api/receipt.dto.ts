import type { ReceiptStatus } from "../model/receipt.types";
export interface CreateReceiptDraftLineResponseDTO {
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
}
export interface CreateReceiptDraftResponseDTO {
  id: string;
  operation_type: "RECEIPT";
  status: ReceiptStatus;
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
  lines: CreateReceiptDraftLineResponseDTO[];
}
export interface GetReceiptDocumentLineResponseDTO {
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
}
export interface GetReceiptDocumentResponseDTO {
  id: string;
  operation_type: "RECEIPT";
  status: ReceiptStatus;
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
  lines: GetReceiptDocumentLineResponseDTO[];
}
export interface ReceiptListItemResponseDTO {
  id: string;
  operation_type: "RECEIPT";
  status: ReceiptStatus;
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
export interface ListReceiptDocumentsResponseDTO {
  items: ReceiptListItemResponseDTO[];
  total: number;
  offset: number;
  limit: number;
}
export interface CreateReceiptDraftRequestDTO {
  warehouse_id: string;
  owner_id: string;
  lines: { inventory_item_id: string; quantity: string; uom: string }[];
}
