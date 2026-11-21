export type InternalMoveStatus =
  "DRAFT" | "CONFIRMED" | "PARTIALLY_EXECUTED" | "COMPLETED" | "CANCELLED";
export interface InternalMoveLine {
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
export interface InternalMoveDocument {
  id: string;
  operationType: "INTERNAL_MOVE";
  status: InternalMoveStatus;
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
  lines: InternalMoveLine[];
}
export interface InternalMoveListItem extends Omit<
  InternalMoveDocument,
  "lines"
> {
  lineCount: number;
}
export interface InternalMovesPage {
  items: InternalMoveListItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface InternalMovesParams {
  search: string;
  warehouseId?: string;
  ownerId?: string;
  status: InternalMoveStatus | "ALL";
  createdFrom?: string;
  createdTo?: string;
  offset: number;
  limit: number;
}
export interface InternalMoveDraftLine {
  id?: string;
  key: string;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  quantity: string;
  uom: string;
}
export interface InternalMoveDraftValues {
  warehouseId: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string;
  lines: InternalMoveDraftLine[];
}
export interface InternalMoveLineErrors {
  inventoryItemId?: string;
  quantity?: string;
  uom?: string;
  error?: string;
}
export interface InternalMoveErrors {
  warehouseId?: string;
  ownerId?: string;
  lines?: string;
  lineFields: Record<string, InternalMoveLineErrors>;
}
export interface InternalMoveReferenceOption {
  id: string;
  name: string;
}

export interface InternalMoveEditValues {
  expectedVersion: number;
  lines: InternalMoveDraftLine[];
}
export interface InternalMoveVersionValues {
  expectedVersion: number;
}
