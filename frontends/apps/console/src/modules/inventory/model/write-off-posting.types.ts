export interface WriteOffPreparationLine {
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
export interface WriteOffPreparation {
  documentId: string;
  version: number;
  status: string;
  warehouseId: string;
  reason: string;
  lines: WriteOffPreparationLine[];
}
export interface WriteOffSource {
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
export interface WriteOffSources {
  items: WriteOffSource[];
  total: number;
  offset: number;
  limit: number;
}
export interface WriteOffSourceParams {
  documentLineId: string;
  search: string;
  offset: number;
  positionId?: string;
}
export interface WriteOffAllocation extends WriteOffPreparationLine {
  key: string;
  selected: boolean;
  quantity: string;
  uom: string;
  source: WriteOffSource | null;
  sourceMissing: boolean;
}
export interface WriteOffExecutionValues {
  expectedVersion: number;
  rows: WriteOffAllocation[];
}
export interface WriteOffExecutionErrors {
  form?: string;
  rows: Record<string, string>;
  lines: Record<string, string>;
}
export interface WriteOffExecutionHistoryItem {
  executionId: string;
  postingId: string;
  postedAt: string;
  documentVersionAfter: number;
  documentStatus: string;
  reason: string;
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
export interface WriteOffExecutionHistory {
  items: WriteOffExecutionHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface WriteOffPostingResult {
  documentId: string;
  executionId: string;
  postingId: string;
  documentVersionAfter: number;
  documentStatus: string;
}
