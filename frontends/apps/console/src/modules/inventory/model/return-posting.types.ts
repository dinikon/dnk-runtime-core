export interface ReturnPreparationLine {
  documentLineId: string;
  originExecutionLineId: string;
  originalQuantity: string;
  returnedQuantity: string;
  returnableQuantity: string;
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
export interface ReturnPreparation {
  documentId: string;
  version: number;
  status: string;
  warehouseId: string;
  reason: string;
  direction: string;
  originExecutionId: string;
  lines: ReturnPreparationLine[];
}
export interface ReturnSource {
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
export interface ReturnSources {
  items: ReturnSource[];
  total: number;
  offset: number;
  limit: number;
}
export interface ReturnSourceParams {
  documentLineId: string;
  search: string;
  offset: number;
  positionId?: string;
}
export interface ReturnAllocation extends ReturnPreparationLine {
  key: string;
  selected: boolean;
  quantity: string;
  uom: string;
  source: ReturnSource | null;
  sourceMissing: boolean;
  direction: string;
  destination: ReturnDestination | null;
  stockStatus: string;
}
export interface ReturnExecutionValues {
  expectedVersion: number;
  rows: ReturnAllocation[];
}
export interface ReturnExecutionErrors {
  form?: string;
  rows: Record<string, string>;
  lines: Record<string, string>;
}
export interface ReturnExecutionHistoryItem {
  executionId: string;
  postingId: string;
  postedAt: string;
  documentVersionAfter: number;
  documentStatus: string;
  reason: string;
  direction: string;
  originExecutionId: string;
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
export interface ReturnExecutionHistory {
  items: ReturnExecutionHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface ReturnPostingResult {
  originExecutionId: string;
  documentId: string;
  executionId: string;
  postingId: string;
  documentVersionAfter: number;
  documentStatus: string;
}

export interface ReturnDestination {
  id: string;
  code: string;
  name: string;
}
export interface ReturnDestinations {
  items: ReturnDestination[];
  total: number;
  offset: number;
  limit: number;
}
export interface ReturnDestinationParams {
  search: string;
  offset: number;
  locationId?: string;
}
