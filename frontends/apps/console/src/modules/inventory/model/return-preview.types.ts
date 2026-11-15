export interface ReturnPreviewPosition {
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
export interface ReturnPreview {
  documentId: string;
  version: number;
  reason: string;
  direction: string;
  originExecutionId: string;
  positions: ReturnPreviewPosition[];
}
