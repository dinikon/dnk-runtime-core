export type IssueStatus =
  "DRAFT" | "CONFIRMED" | "PARTIALLY_EXECUTED" | "COMPLETED" | "CANCELLED";
export interface IssueLine {
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
export interface IssueDocument {
  id: string;
  operationType: "ISSUE";
  status: IssueStatus;
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
  lines: IssueLine[];
}
export interface IssueListItem extends Omit<IssueDocument, "lines"> {
  lineCount: number;
}
export interface IssuesPage {
  items: IssueListItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface IssuesParams {
  search: string;
  warehouseId?: string;
  ownerId?: string;
  status: IssueStatus | "ALL";
  createdFrom?: string;
  createdTo?: string;
  offset: number;
  limit: number;
}
export interface IssueDraftLine {
  id?: string;
  key: string;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  quantity: string;
  uom: string;
}
export interface IssueDraftValues {
  warehouseId: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string;
  lines: IssueDraftLine[];
}
export interface IssueLineErrors {
  inventoryItemId?: string;
  quantity?: string;
  uom?: string;
  error?: string;
}
export interface IssueErrors {
  warehouseId?: string;
  ownerId?: string;
  lines?: string;
  lineFields: Record<string, IssueLineErrors>;
}
export interface IssueReferenceOption {
  id: string;
  name: string;
}

export interface IssueEditValues {
  expectedVersion: number;
  lines: IssueDraftLine[];
}
export interface IssueVersionValues {
  expectedVersion: number;
}
