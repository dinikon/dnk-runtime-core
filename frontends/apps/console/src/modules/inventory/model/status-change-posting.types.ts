export interface StatusChangePreparationLine {
  documentLineId: string;
  position: number;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  currentBaseUom: string;
  plannedQuantity: string;
  executedQuantity: string;
  remainingQuantity: string;
  quantityStep: string;
  trackingMode: "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
  expirationMode: "NONE" | "OPTIONAL" | "REQUIRED";
}
export interface StatusChangePreparation {
  documentId: string;
  version: number;
  status: string;
  warehouseId: string;
  reason: string;
  targetStatus: string;
  lines: StatusChangePreparationLine[];
}
export interface StatusChangeSource {
  id: string;
  inventoryItemId: string;
  locationId: string;
  locationCode: string;
  stockStatus: string;
  lotId: string | null;
  lotNumber: string | null;
  serialId: string | null;
  serialNumber: string | null;
  manufacturedOn: string | null;
  expiresOn: string | null;
  baseUom: string;
  onHandQuantity: string;
  version: number;
}
export interface StatusChangeSources {
  items: StatusChangeSource[];
  total: number;
  offset: number;
  limit: number;
}
export interface StatusChangeSourceParams {
  documentLineId: string;
  search: string;
  offset: number;
  positionId?: string;
}
export interface StatusChangeAllocation extends StatusChangePreparationLine {
  key: string;
  selected: boolean;
  quantity: string;
  uom: string;
  source: StatusChangeSource | null;
  sourceMissing: boolean;
}
export interface StatusChangeExecutionValues {
  expectedVersion: number;
  rows: StatusChangeAllocation[];
}
export interface StatusChangeExecutionErrors {
  form?: string;
  rows: Record<string, string>;
  lines: Record<string, string>;
}
export interface StatusChangeExecutionHistoryItem {
  executionId: string;
  postingId: string;
  postedAt: string;
  documentVersionAfter: number;
  documentStatus: string;
  reason: string;
  targetStatus: string;
  lineCount: number;
  lines: {
    documentLineId: string;
    position: number;
    sku: string;
    baseUom: string;
    quantity: string;
    allocationCount: number;
  }[];
}
export interface StatusChangeExecutionHistory {
  items: StatusChangeExecutionHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface StatusChangePostingResult {
  documentId: string;
  executionId: string;
  postingId: string;
  documentVersionAfter: number;
  documentStatus: string;
}
