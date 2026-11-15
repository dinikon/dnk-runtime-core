export interface ListStockPositionsItem {
  id: string;
  inventoryItemId: string;
  sku: string;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  warehouseIsActive: boolean;
  locationId: string;
  locationCode: string;
  locationName: string;
  locationIsActive: boolean;
  ownerId: string;
  ownerName: string | null;
  lotId: string | null;
  lotNumber: string | null;
  serialId: string | null;
  serialNumber: string | null;
  stockStatus: string;
  baseUom: string;
  manufacturedOn: string | null;
  expiresOn: string | null;
  onHandQty: string;
  version: number;
}
export interface ListStockPositionsResult {
  items: ListStockPositionsItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface GetStockPositionResult {
  id: string;
  inventoryItemId: string;
  sku: string;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  warehouseIsActive: boolean;
  locationId: string;
  locationCode: string;
  locationName: string;
  locationIsActive: boolean;
  ownerId: string;
  ownerName: string | null;
  lotId: string | null;
  lotNumber: string | null;
  serialId: string | null;
  serialNumber: string | null;
  stockStatus: string;
  baseUom: string;
  manufacturedOn: string | null;
  expiresOn: string | null;
  onHandQty: string;
  version: number;
  ledgerQuantity: string;
}
export interface ListStockMovementsItem {
  id: string;
  positionId: string;
  inventoryItemId: string;
  sku: string;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  warehouseIsActive: boolean;
  locationId: string;
  locationCode: string;
  locationName: string;
  locationIsActive: boolean;
  ownerId: string;
  ownerName: string | null;
  lotId: string | null;
  lotNumber: string | null;
  serialId: string | null;
  serialNumber: string | null;
  stockStatus: string;
  baseUom: string;
  manufacturedOn: string | null;
  expiresOn: string | null;
  documentId: string;
  executionId: string;
  postingId: string;
  documentStatus: string;
  operationType: string;
  postedAt: string;
  quantityDelta: string;
  executionLineIds: string[];
  historicalSkus: string[];
  writeOffReason: string | null;
  operationReason?: string | null;
  targetStatus?: string | null;
  returnDirection?: string | null;
  originExecutionId?: string | null;
}
export interface MovementPositionSnapshot {
  id: string;
  quantity: string;
  version: number;
}
export interface ListStockMovementsResult {
  items: ListStockMovementsItem[];
  total: number;
  offset: number;
  limit: number;
  position: MovementPositionSnapshot | null;
}
export interface ListStockExecutionsItem {
  id: string;
  documentId: string;
  documentStatus: string;
  documentVersion: number;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  operationType: string;
  executedAt: string;
  postingId: string | null;
  lineCount: number;
}
export interface ListStockExecutionsResult {
  items: ListStockExecutionsItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface ListStockPostingsItem {
  id: string;
  executionId: string;
  documentId: string;
  documentStatus: string;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  operationType: string;
  postedAt: string;
  entryCount: number;
}
export interface ListStockPostingsResult {
  items: ListStockPostingsItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface GetStockExecutionDetailsLine {
  id: string;
  documentLineId: string;
  inventoryItemId: string;
  sku: string;
  skuAtDocument: string;
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
  ledgerEntryIds: string[];
  skuAtReceipt: string | null;
  serialNumberAtReceipt: string | null;
  locationCodeAtReceipt: string | null;
  destinationLocationId: string | null;
  destinationLocationCode: string | null;
  destinationStockStatus?: string | null;
  originExecutionLineId?: string | null;
  sourceLedgerEntryId: string | null;
  destinationLedgerEntryId: string | null;
}
export interface GetStockExecutionDetailsEntry {
  id: string;
  positionId: string;
  quantityDelta: string;
  baseUom: string;
  executionLineIds: string[];
}
export interface GetStockExecutionDetailsAllocation {
  executionLineId: string;
  amount: string;
}
export interface GetStockExecutionDetailsCost {
  id: string;
  amount: string;
  currency: string;
  basisKind: string;
  sourceSystem: string | null;
  sourceReference: string | null;
  allocations: GetStockExecutionDetailsAllocation[];
}
export interface GetStockExecutionDetailsResult {
  id: string;
  executionId: string;
  postingId: string | null;
  documentId: string;
  documentVersionAtExecution: number;
  documentCurrentVersion: number;
  documentCurrentStatus: string;
  operationType: string;
  executedAt: string;
  postedAt: string | null;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  hasReceiptResult: boolean;
  writeOffReason: string | null;
  operationReason?: string | null;
  targetStatus?: string | null;
  returnDirection?: string | null;
  originExecutionId?: string | null;
  lines: GetStockExecutionDetailsLine[];
  ledger: GetStockExecutionDetailsEntry[];
  costs: GetStockExecutionDetailsCost[];
}
export interface GetStockPostingDetailsLine {
  id: string;
  documentLineId: string;
  inventoryItemId: string;
  sku: string;
  skuAtDocument: string;
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
  ledgerEntryIds: string[];
  skuAtReceipt: string | null;
  serialNumberAtReceipt: string | null;
  locationCodeAtReceipt: string | null;
  destinationLocationId: string | null;
  destinationLocationCode: string | null;
  destinationStockStatus?: string | null;
  originExecutionLineId?: string | null;
  sourceLedgerEntryId: string | null;
  destinationLedgerEntryId: string | null;
}
export interface GetStockPostingDetailsEntry {
  id: string;
  positionId: string;
  quantityDelta: string;
  baseUom: string;
  executionLineIds: string[];
}
export interface GetStockPostingDetailsAllocation {
  executionLineId: string;
  amount: string;
}
export interface GetStockPostingDetailsCost {
  id: string;
  amount: string;
  currency: string;
  basisKind: string;
  sourceSystem: string | null;
  sourceReference: string | null;
  allocations: GetStockPostingDetailsAllocation[];
}
export interface GetStockPostingDetailsResult {
  id: string;
  executionId: string;
  postingId: string | null;
  documentId: string;
  documentVersionAtExecution: number;
  documentCurrentVersion: number;
  documentCurrentStatus: string;
  operationType: string;
  executedAt: string;
  postedAt: string | null;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  ownerId: string;
  ownerName: string | null;
  hasReceiptResult: boolean;
  writeOffReason: string | null;
  operationReason?: string | null;
  targetStatus?: string | null;
  returnDirection?: string | null;
  originExecutionId?: string | null;
  lines: GetStockPostingDetailsLine[];
  ledger: GetStockPostingDetailsEntry[];
  costs: GetStockPostingDetailsCost[];
}
export interface StockFilters {
  warehouseId?: string;
  locationId?: string;
  ownerId?: string;
  inventoryItemId?: string;
  lotId?: string;
  serialId?: string;
  positionId?: string;
  documentId?: string;
  executionId?: string;
  postingId?: string;
  stockStatus?: string;
  operationType?: string;
  postedFrom?: string;
  postedTo?: string;
  search?: string;
  includeZero?: boolean;
}
export interface StockReadParams {
  filters: StockFilters;
  offset: number;
  limit: number;
}
export type StockReadKind =
  "positions" | "movements" | "executions" | "postings";
export type StockFilterKind =
  | "warehouseId"
  | "locationId"
  | "ownerId"
  | "inventoryItemId"
  | "lotId"
  | "serialId";
export interface StockFilterOption {
  id: string;
  label: string;
}
export interface StockFilterOptionsPage {
  items: StockFilterOption[];
  total: number;
}

export interface StockTrackingColumns {
  lot: boolean;
  serial: boolean;
}

export interface ListStockBalancesItem {
  key: string;
  inventoryItemId: string;
  sku: string;
  warehouseId: string;
  warehouseCode: string;
  warehouseName: string;
  warehouseIsActive: boolean;
  locationId: string;
  locationCode: string;
  locationName: string;
  locationIsActive: boolean;
  ownerId: string;
  ownerName: string | null;
  lotId: string | null;
  lotNumber: string | null;
  serialId: string | null;
  serialNumber: string | null;
  stockStatus: string;
  baseUom: string;
  manufacturedOn: string | null;
  expiresOn: string | null;
  onHandQty: string;
  positionCount: number;
  lotCount: number;
  serialCount: number;
}
export interface ListStockBalancesResult {
  items: ListStockBalancesItem[];
  total: number;
  offset: number;
  limit: number;
}
export interface StockBalancesParams extends StockReadParams {
  groupByLot: boolean;
  groupBySerial: boolean;
}
