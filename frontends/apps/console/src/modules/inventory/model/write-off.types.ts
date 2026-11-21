export type WriteOffStatus =
  "DRAFT" | "CONFIRMED" | "PARTIALLY_EXECUTED" | "COMPLETED" | "CANCELLED";
export interface WriteOffLine {
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
  remainingQty: string;
}
export interface WriteOffDocument {
  id: string;
  operationType: "WRITE_OFF";
  status: WriteOffStatus;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  reason: string;
  sourceSystem: string | null;
  sourceReference: string | null;
  sourceVersion: number | null;
  createdAt: string;
  updatedAt: string;
  version: number;
  lines: WriteOffLine[];
}
export interface WriteOffListItem extends Omit<WriteOffDocument, "lines"> {
  lineCount: number;
}
export interface WriteOffsPage {
  items: WriteOffListItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface WriteOffsParams {
  search: string;
  warehouseId?: string;
  ownerId?: string;
  status: WriteOffStatus | "ALL";
  createdFrom?: string;
  createdTo?: string;
  offset: number;
  limit: number;
}
export interface WriteOffDraftLine {
  id?: string;
  key: string;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  quantity: string;
  uom: string;
}
export interface WriteOffDraftValues {
  warehouseId: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string;
  reason: string;
  lines: WriteOffDraftLine[];
}
export interface WriteOffLineErrors {
  inventoryItemId?: string;
  quantity?: string;
  uom?: string;
  error?: string;
}
export interface WriteOffErrors {
  reason?: string;
  warehouseId?: string;
  ownerId?: string;
  lines?: string;
  lineFields: Record<string, WriteOffLineErrors>;
}
export interface WriteOffReferenceOption {
  id: string;
  name: string;
}

export interface WriteOffEditValues {
  reason: string;
  expectedVersion: number;
  lines: WriteOffDraftLine[];
}
export interface WriteOffVersionValues {
  expectedVersion: number;
}
