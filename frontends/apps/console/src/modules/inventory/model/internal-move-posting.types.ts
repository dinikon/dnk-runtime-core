export interface InternalMovePreparationLine {
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
export interface InternalMovePreparation {
  documentId: string;
  version: number;
  status: string;
  warehouseId: string;
  lines: InternalMovePreparationLine[];
}
export interface InternalMoveSource {
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
export interface InternalMoveSources {
  items: InternalMoveSource[];
  total: number;
  offset: number;
  limit: number;
}
export interface InternalMoveSourceParams {
  documentLineId: string;
  search: string;
  offset: number;
  positionId?: string;
}
export interface InternalMoveAllocation extends InternalMovePreparationLine {
  key: string;
  selected: boolean;
  quantity: string;
  uom: string;
  source: InternalMoveSource | null;
  sourceMissing: boolean;
  destination: InternalMoveDestination | null;
  destinationMissing: boolean;
}
export interface InternalMoveExecutionValues {
  expectedVersion: number;
  rows: InternalMoveAllocation[];
}
export interface InternalMoveExecutionErrors {
  form?: string;
  rows: Record<string, string>;
  lines: Record<string, string>;
}
export interface InternalMoveExecutionHistoryItem {
  executionId: string;
  postingId: string;
  postedAt: string;
  documentVersionAfter: number;
  documentStatus: string;
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
export interface InternalMoveExecutionHistory {
  items: InternalMoveExecutionHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface InternalMovePostingResult {
  documentId: string;
  executionId: string;
  postingId: string;
  documentVersionAfter: number;
  documentStatus: string;
}

export interface InternalMoveDestination {
  id: string;
  code: string;
  name: string;
}
export interface InternalMoveDestinations {
  items: InternalMoveDestination[];
  total: number;
  offset: number;
  limit: number;
}
export interface InternalMoveDestinationParams {
  search: string;
  offset: number;
  locationId?: string;
}
