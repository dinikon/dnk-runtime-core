export interface StatusTransition {
  sourceStatus: string;
  targetStatuses: string[];
}
export interface StatusChangePreviewPosition {
  id: string | null;
  exists: boolean;
  role: "SOURCE" | "DESTINATION";
  inventoryItemId: string;
  sku: string;
  locationCode: string;
  stockStatus: string;
  lotNumber: string | null;
  serialNumber: string | null;
  baseUom: string;
  before: string;
  delta: string;
  after: string;
}
export interface StatusChangePreview {
  documentId: string;
  version: number;
  reason: string;
  targetStatus: string;
  positions: StatusChangePreviewPosition[];
}
