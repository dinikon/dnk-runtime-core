export interface IssuePreparationLine {
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
export interface IssuePreparation {
  documentId: string;
  version: number;
  status: string;
  warehouseId: string;
  lines: IssuePreparationLine[];
}
export interface IssueSource {
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
export interface IssueSources {
  items: IssueSource[];
  total: number;
  offset: number;
  limit: number;
}
export interface IssueSourceParams {
  documentLineId: string;
  search: string;
  offset: number;
  positionId?: string;
}
export interface IssueAllocation extends IssuePreparationLine {
  key: string;
  selected: boolean;
  quantity: string;
  uom: string;
  source: IssueSource | null;
  sourceMissing: boolean;
}
export interface IssueExecutionValues {
  expectedVersion: number;
  rows: IssueAllocation[];
}
export interface IssueExecutionErrors {
  form?: string;
  rows: Record<string, string>;
  lines: Record<string, string>;
}
export interface IssueExecutionHistoryItem {
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
export interface IssueExecutionHistory {
  items: IssueExecutionHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface IssuePostingResult {
  documentId: string;
  executionId: string;
  postingId: string;
  documentVersionAfter: number;
  documentStatus: string;
}
