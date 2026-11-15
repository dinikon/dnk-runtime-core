export type ReceiptStatus =
  "DRAFT" | "CONFIRMED" | "PARTIALLY_EXECUTED" | "COMPLETED" | "CANCELLED";
export interface ReceiptLine {
  id: string;
  position: number;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  plannedQty: string;
  sourceQuantity: string;
  sourceUom: string;
  factorToBase: string;
  executedQty: string;
}
export interface ReceiptDocument {
  id: string;
  operationType: "RECEIPT";
  status: ReceiptStatus;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  sourceSystem: string | null;
  sourceReference: string | null;
  sourceVersion: number | null;
  createdAt: string;
  updatedAt: string;
  version: number;
  lines: ReceiptLine[];
}
export interface ReceiptListItem extends Omit<ReceiptDocument, "lines"> {
  lineCount: number;
}
export interface ReceiptsPage {
  items: ReceiptListItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface ReceiptsParams {
  search: string;
  warehouseId?: string;
  ownerId?: string;
  status: ReceiptStatus | "ALL";
  createdFrom?: string;
  createdTo?: string;
  offset: number;
  limit: number;
}
export interface ReceiptDraftLine {
  key: string;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  quantity: string;
  uom: string;
}
export interface ReceiptDraftValues {
  warehouseId: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string;
  lines: ReceiptDraftLine[];
}
export interface ReceiptLineErrors {
  inventoryItemId?: string;
  quantity?: string;
  uom?: string;
  error?: string;
}
export interface ReceiptErrors {
  warehouseId?: string;
  ownerId?: string;
  lines?: string;
  lineFields: Record<string, ReceiptLineErrors>;
}
export interface ReceiptReferenceOption {
  id: string;
  name: string;
}
