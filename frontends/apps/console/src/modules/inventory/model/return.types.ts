export type ReturnStatus =
  "DRAFT" | "CONFIRMED" | "PARTIALLY_EXECUTED" | "COMPLETED" | "CANCELLED";
export interface ReturnLine {
  originExecutionLineId: string;
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
export interface ReturnDocument {
  id: string;
  operationType: "RETURN";
  status: ReturnStatus;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  reason: string;
  direction: string;
  originExecutionId: string;
  sourceSystem: string | null;
  sourceReference: string | null;
  sourceVersion: number | null;
  createdAt: string;
  updatedAt: string;
  version: number;
  lines: ReturnLine[];
}
export interface ReturnListItem extends Omit<ReturnDocument, "lines"> {
  lineCount: number;
}
export interface ReturnsPage {
  items: ReturnListItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface ReturnsParams {
  originExecutionId?: string;
  search: string;
  warehouseId?: string;
  ownerId?: string;
  status: ReturnStatus | "ALL";
  createdFrom?: string;
  createdTo?: string;
  offset: number;
  limit: number;
}
export interface ReturnDraftLine {
  originExecutionLineId: string;
  id?: string;
  key: string;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  quantity: string;
  uom: string;
}
export interface ReturnDraftValues {
  originExecutionId: string;
  reason: string;
  lines: ReturnDraftLine[];
}
export interface ReturnLineErrors {
  inventoryItemId?: string;
  quantity?: string;
  uom?: string;
  error?: string;
}
export interface ReturnErrors {
  originExecutionId?: string;
  reason?: string;
  warehouseId?: string;
  ownerId?: string;
  lines?: string;
  lineFields: Record<string, ReturnLineErrors>;
}
export interface ReturnReferenceOption {
  id: string;
  name: string;
}

export interface ReturnEditValues {
  reason: string;
  expectedVersion: number;
  lines: ReturnDraftLine[];
}
export interface ReturnVersionValues {
  expectedVersion: number;
}
