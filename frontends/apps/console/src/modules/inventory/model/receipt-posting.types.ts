export interface ReceiptPostingLine {
  id: string;
  clientLineId: string;
  documentLineId: string;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  quantity: string;
  sourceQuantity: string;
  sourceUom: string;
  factorToBase: string;
  locationId: string;
  locationCode: string;
  lotId: string | null;
  lotNumber: string | null;
  serialId: string | null;
  serialNumber: string | null;
  stockStatus: string;
  positionId: string;
  ledgerEntryId: string;
}
export interface ReceiptPostingPosition {
  id: string;
  baseUom: string;
  beforeQuantity: string;
  delta: string;
  afterQuantity: string;
  beforeVersion: number;
  afterVersion: number;
}
export interface ReceiptPostingEntry {
  id: string;
  positionId: string;
  quantityDelta: string;
  baseUom: string;
}
export interface ReceiptPostingAllocation {
  executionLineId: string;
  amount: string;
}
export interface ReceiptPostingCost {
  id: string;
  amount: string;
  currency: string;
  basisKind: string;
  sourceSystem: string | null;
  sourceReference: string | null;
  allocations: ReceiptPostingAllocation[];
}
export interface ReceiptPostingResult {
  documentId: string;
  documentVersionBefore: number;
  documentVersionAfter: number;
  documentStatus: string;
  executionId: string;
  postingId: string;
  eventId: string;
  actorId: string;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  postedAt: string;
  lines: ReceiptPostingLine[];
  positions: ReceiptPostingPosition[];
  ledger: ReceiptPostingEntry[];
  costs: ReceiptPostingCost[];
}

export type ReceiptTrackingMode = "NONE" | "LOT" | "SERIAL" | "LOT_AND_SERIAL";
export type ReceiptReferenceKind = "locations" | "lots" | "serials";
export interface ReceiptPreparationLine {
  documentLineId: string;
  position: number;
  plannedQuantity: string;
  executedQuantity: string;
  inventoryItemId: string;
  sku: string;
  baseUom: string;
  currentBaseUom: string;
  remainingQuantity: string;
  quantityStep: string;
  trackingMode: ReceiptTrackingMode;
  expirationMode: "NONE" | "OPTIONAL" | "REQUIRED";
}
export interface ReceiptPreparation {
  documentId: string;
  version: number;
  status: string;
  warehouseId: string;
  defaultStorageLocationId: string | null;
  lines: ReceiptPreparationLine[];
}
export interface IntakeRow extends ReceiptPreparationLine {
  selected: boolean;
  key: string;
  quantity: string;
  uom: string;
  locationId: string;
  locationLabel: string;
  lotId: string;
  lotNumber: string;
  serialId: string;
  serialNumber: string;
  manufacturedOn: string | null;
  expiresOn: string | null;
  stockStatus: "SELLABLE" | "QUARANTINE" | "DAMAGED" | "BLOCKED";
  costKnown: boolean;
  costAmount: string;
  costCurrency: string;
  costReference: string;
}
export interface IntakeUnallocatedCost {
  known: boolean;
  amount: string;
  currency: string;
  reference: string;
}
export interface ReceiptIntakeValues {
  expectedVersion: number;
  rows: IntakeRow[];
  unallocatedCost: IntakeUnallocatedCost;
}
export interface ReceiptIntakeErrors {
  rows: Record<string, string>;
  lines?: Record<string, string>;
  costs?: string;
  form?: string;
}
export interface IntakeReference {
  id: string;
  label: string;
  lotId: string | null;
  lotNumber: string | null;
  manufacturedOn: string | null;
  expiresOn: string | null;
}
export interface IntakeReferencesPage {
  items: IntakeReference[];
  total: number;
  offset: number;
  limit: number;
}
export interface ReceiptReferencesParams {
  kind: ReceiptReferenceKind;
  documentLineId?: string;
  lotId?: string;
  search: string;
  offset: number;
  limit: number;
}
export interface ReceiptExecutionHistoryLine {
  documentLineId: string;
  position: number;
  sku: string;
  baseUom: string;
  quantity: string;
  allocationCount: number;
}
export interface ReceiptIntakeGroup {
  line: ReceiptPreparationLine;
  current: ReceiptPreparationLine | undefined;
  rows: IntakeRow[];
}
export interface ReceiptExecutionHistoryItem {
  executionId: string;
  postingId: string;
  postedAt: string;
  documentVersionAfter: number;
  documentStatus: string;
  lineCount: number;
  lines: ReceiptExecutionHistoryLine[];
}
export interface ReceiptExecutionHistory {
  items: ReceiptExecutionHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}
