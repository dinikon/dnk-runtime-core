export type StatusChangeStatus =
  "DRAFT" | "CONFIRMED" | "PARTIALLY_EXECUTED" | "COMPLETED" | "CANCELLED";
export interface StatusChangeLine {
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
export interface StatusChangeDocument {
  id: string;
  operationType: "STATUS_CHANGE";
  status: StatusChangeStatus;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  reason: string;
  targetStatus: string;
  sourceSystem: string | null;
  sourceReference: string | null;
  sourceVersion: number | null;
  createdAt: string;
  updatedAt: string;
  version: number;
  lines: StatusChangeLine[];
}
export interface StatusChangeListItem extends Omit<
  StatusChangeDocument,
  "lines"
> {
  lineCount: number;
}
export interface StatusChangesPage {
  items: StatusChangeListItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface StatusChangesParams {
  search: string;
  warehouseId?: string;
  ownerId?: string;
  status: StatusChangeStatus | "ALL";
  createdFrom?: string;
  createdTo?: string;
  offset: number;
  limit: number;
}
export interface StatusChangeDraftLine {
  id?: string;
  key: string;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  quantity: string;
  uom: string;
}
export interface StatusChangeDraftValues {
  warehouseId: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string;
  reason: string;
  targetStatus: string;
  lines: StatusChangeDraftLine[];
}
export interface StatusChangeLineErrors {
  inventoryItemId?: string;
  quantity?: string;
  uom?: string;
  error?: string;
}
export interface StatusChangeErrors {
  targetStatus?: string;
  reason?: string;
  warehouseId?: string;
  ownerId?: string;
  lines?: string;
  lineFields: Record<string, StatusChangeLineErrors>;
}
export interface StatusChangeReferenceOption {
  id: string;
  name: string;
}

export interface StatusChangeEditValues {
  reason: string;
  targetStatus: string;
  expectedVersion: number;
  lines: StatusChangeDraftLine[];
}
export interface StatusChangeVersionValues {
  expectedVersion: number;
}
