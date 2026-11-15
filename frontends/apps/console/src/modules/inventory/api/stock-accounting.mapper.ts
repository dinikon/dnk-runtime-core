import type {
  ListStockBalancesItem,
  ListStockBalancesResult,
} from "../model/stock-accounting.types";
import type {
  ListStockBalancesItemDTO,
  ListStockBalancesResultDTO,
} from "./stock-accounting.dto";
import type {
  ListStockPositionsItem,
  ListStockPositionsResult,
  GetStockPositionResult,
  ListStockMovementsItem,
  MovementPositionSnapshot,
  ListStockMovementsResult,
  ListStockExecutionsItem,
  ListStockExecutionsResult,
  ListStockPostingsItem,
  ListStockPostingsResult,
  GetStockExecutionDetailsLine,
  GetStockExecutionDetailsEntry,
  GetStockExecutionDetailsAllocation,
  GetStockExecutionDetailsCost,
  GetStockExecutionDetailsResult,
  GetStockPostingDetailsLine,
  GetStockPostingDetailsEntry,
  GetStockPostingDetailsAllocation,
  GetStockPostingDetailsCost,
  GetStockPostingDetailsResult,
} from "../model/stock-accounting.types";
import type {
  ListStockPositionsItemDTO,
  ListStockPositionsResultDTO,
  GetStockPositionResultDTO,
  ListStockMovementsItemDTO,
  MovementPositionSnapshotDTO,
  ListStockMovementsResultDTO,
  ListStockExecutionsItemDTO,
  ListStockExecutionsResultDTO,
  ListStockPostingsItemDTO,
  ListStockPostingsResultDTO,
  GetStockExecutionDetailsLineDTO,
  GetStockExecutionDetailsEntryDTO,
  GetStockExecutionDetailsAllocationDTO,
  GetStockExecutionDetailsCostDTO,
  GetStockExecutionDetailsResultDTO,
  GetStockPostingDetailsLineDTO,
  GetStockPostingDetailsEntryDTO,
  GetStockPostingDetailsAllocationDTO,
  GetStockPostingDetailsCostDTO,
  GetStockPostingDetailsResultDTO,
} from "./stock-accounting.dto";
export function listStockPositionsItemFromDto(
  dto: ListStockPositionsItemDTO,
): ListStockPositionsItem {
  return {
    id: dto.id,
    inventoryItemId: dto.inventory_item_id,
    sku: dto.sku,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    warehouseIsActive: dto.warehouse_is_active,
    locationId: dto.location_id,
    locationCode: dto.location_code,
    locationName: dto.location_name,
    locationIsActive: dto.location_is_active,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    lotId: dto.lot_id,
    lotNumber: dto.lot_number,
    serialId: dto.serial_id,
    serialNumber: dto.serial_number,
    stockStatus: dto.stock_status,
    baseUom: dto.base_uom,
    manufacturedOn: dto.manufactured_on,
    expiresOn: dto.expires_on,
    onHandQty: dto.on_hand_qty,
    version: dto.version,
  };
}
export function listStockPositionsResultFromDto(
  dto: ListStockPositionsResultDTO,
): ListStockPositionsResult {
  return {
    items: dto.items.map(listStockPositionsItemFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
export function getStockPositionResultFromDto(
  dto: GetStockPositionResultDTO,
): GetStockPositionResult {
  return {
    id: dto.id,
    inventoryItemId: dto.inventory_item_id,
    sku: dto.sku,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    warehouseIsActive: dto.warehouse_is_active,
    locationId: dto.location_id,
    locationCode: dto.location_code,
    locationName: dto.location_name,
    locationIsActive: dto.location_is_active,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    lotId: dto.lot_id,
    lotNumber: dto.lot_number,
    serialId: dto.serial_id,
    serialNumber: dto.serial_number,
    stockStatus: dto.stock_status,
    baseUom: dto.base_uom,
    manufacturedOn: dto.manufactured_on,
    expiresOn: dto.expires_on,
    onHandQty: dto.on_hand_qty,
    version: dto.version,
    ledgerQuantity: dto.ledger_quantity,
  };
}
export function listStockMovementsItemFromDto(
  dto: ListStockMovementsItemDTO,
): ListStockMovementsItem {
  return {
    id: dto.id,
    positionId: dto.position_id,
    inventoryItemId: dto.inventory_item_id,
    sku: dto.sku,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    warehouseIsActive: dto.warehouse_is_active,
    locationId: dto.location_id,
    locationCode: dto.location_code,
    locationName: dto.location_name,
    locationIsActive: dto.location_is_active,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    lotId: dto.lot_id,
    lotNumber: dto.lot_number,
    serialId: dto.serial_id,
    serialNumber: dto.serial_number,
    stockStatus: dto.stock_status,
    baseUom: dto.base_uom,
    manufacturedOn: dto.manufactured_on,
    expiresOn: dto.expires_on,
    documentId: dto.document_id,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    documentStatus: dto.document_status,
    operationType: dto.operation_type,
    postedAt: dto.posted_at,
    quantityDelta: dto.quantity_delta,
    executionLineIds: [...dto.execution_line_ids],
    historicalSkus: [...dto.historical_skus],
  };
}
export function movementPositionSnapshotFromDto(
  dto: MovementPositionSnapshotDTO,
): MovementPositionSnapshot {
  return {
    id: dto.id,
    quantity: dto.quantity,
    version: dto.version,
  };
}
export function listStockMovementsResultFromDto(
  dto: ListStockMovementsResultDTO,
): ListStockMovementsResult {
  return {
    items: dto.items.map(listStockMovementsItemFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
    position: dto.position
      ? movementPositionSnapshotFromDto(dto.position)
      : null,
  };
}
export function listStockExecutionsItemFromDto(
  dto: ListStockExecutionsItemDTO,
): ListStockExecutionsItem {
  return {
    id: dto.id,
    documentId: dto.document_id,
    documentStatus: dto.document_status,
    documentVersion: dto.document_version,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    operationType: dto.operation_type,
    executedAt: dto.executed_at,
    postingId: dto.posting_id,
    lineCount: dto.line_count,
  };
}
export function listStockExecutionsResultFromDto(
  dto: ListStockExecutionsResultDTO,
): ListStockExecutionsResult {
  return {
    items: dto.items.map(listStockExecutionsItemFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
export function listStockPostingsItemFromDto(
  dto: ListStockPostingsItemDTO,
): ListStockPostingsItem {
  return {
    id: dto.id,
    executionId: dto.execution_id,
    documentId: dto.document_id,
    documentStatus: dto.document_status,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    operationType: dto.operation_type,
    postedAt: dto.posted_at,
    entryCount: dto.entry_count,
  };
}
export function listStockPostingsResultFromDto(
  dto: ListStockPostingsResultDTO,
): ListStockPostingsResult {
  return {
    items: dto.items.map(listStockPostingsItemFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
export function getStockExecutionDetailsLineFromDto(
  dto: GetStockExecutionDetailsLineDTO,
): GetStockExecutionDetailsLine {
  return {
    id: dto.id,
    documentLineId: dto.document_line_id,
    inventoryItemId: dto.inventory_item_id,
    sku: dto.sku,
    skuAtDocument: dto.sku_at_document,
    baseUom: dto.base_uom,
    quantity: dto.quantity,
    sourceQuantity: dto.source_quantity,
    sourceUom: dto.source_uom,
    factorToBase: dto.factor_to_base,
    locationId: dto.location_id,
    locationCode: dto.location_code,
    lotId: dto.lot_id,
    lotNumber: dto.lot_number,
    serialId: dto.serial_id,
    serialNumber: dto.serial_number,
    stockStatus: dto.stock_status,
    ledgerEntryIds: [...dto.ledger_entry_ids],
    skuAtReceipt: dto.sku_at_receipt,
    serialNumberAtReceipt: dto.serial_number_at_receipt,
    locationCodeAtReceipt: dto.location_code_at_receipt,
  };
}
export function getStockExecutionDetailsEntryFromDto(
  dto: GetStockExecutionDetailsEntryDTO,
): GetStockExecutionDetailsEntry {
  return {
    id: dto.id,
    positionId: dto.position_id,
    quantityDelta: dto.quantity_delta,
    baseUom: dto.base_uom,
    executionLineIds: [...dto.execution_line_ids],
  };
}
export function getStockExecutionDetailsAllocationFromDto(
  dto: GetStockExecutionDetailsAllocationDTO,
): GetStockExecutionDetailsAllocation {
  return {
    executionLineId: dto.execution_line_id,
    amount: dto.amount,
  };
}
export function getStockExecutionDetailsCostFromDto(
  dto: GetStockExecutionDetailsCostDTO,
): GetStockExecutionDetailsCost {
  return {
    id: dto.id,
    amount: dto.amount,
    currency: dto.currency,
    basisKind: dto.basis_kind,
    sourceSystem: dto.source_system,
    sourceReference: dto.source_reference,
    allocations: dto.allocations.map(getStockExecutionDetailsAllocationFromDto),
  };
}
export function getStockExecutionDetailsResultFromDto(
  dto: GetStockExecutionDetailsResultDTO,
): GetStockExecutionDetailsResult {
  return {
    id: dto.id,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    documentId: dto.document_id,
    documentVersionAtExecution: dto.document_version_at_execution,
    documentCurrentVersion: dto.document_current_version,
    documentCurrentStatus: dto.document_current_status,
    operationType: dto.operation_type,
    executedAt: dto.executed_at,
    postedAt: dto.posted_at,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    hasReceiptResult: dto.has_receipt_result,
    lines: dto.lines.map(getStockExecutionDetailsLineFromDto),
    ledger: dto.ledger.map(getStockExecutionDetailsEntryFromDto),
    costs: dto.costs.map(getStockExecutionDetailsCostFromDto),
  };
}
export function getStockPostingDetailsLineFromDto(
  dto: GetStockPostingDetailsLineDTO,
): GetStockPostingDetailsLine {
  return {
    id: dto.id,
    documentLineId: dto.document_line_id,
    inventoryItemId: dto.inventory_item_id,
    sku: dto.sku,
    skuAtDocument: dto.sku_at_document,
    baseUom: dto.base_uom,
    quantity: dto.quantity,
    sourceQuantity: dto.source_quantity,
    sourceUom: dto.source_uom,
    factorToBase: dto.factor_to_base,
    locationId: dto.location_id,
    locationCode: dto.location_code,
    lotId: dto.lot_id,
    lotNumber: dto.lot_number,
    serialId: dto.serial_id,
    serialNumber: dto.serial_number,
    stockStatus: dto.stock_status,
    ledgerEntryIds: [...dto.ledger_entry_ids],
    skuAtReceipt: dto.sku_at_receipt,
    serialNumberAtReceipt: dto.serial_number_at_receipt,
    locationCodeAtReceipt: dto.location_code_at_receipt,
  };
}
export function getStockPostingDetailsEntryFromDto(
  dto: GetStockPostingDetailsEntryDTO,
): GetStockPostingDetailsEntry {
  return {
    id: dto.id,
    positionId: dto.position_id,
    quantityDelta: dto.quantity_delta,
    baseUom: dto.base_uom,
    executionLineIds: [...dto.execution_line_ids],
  };
}
export function getStockPostingDetailsAllocationFromDto(
  dto: GetStockPostingDetailsAllocationDTO,
): GetStockPostingDetailsAllocation {
  return {
    executionLineId: dto.execution_line_id,
    amount: dto.amount,
  };
}
export function getStockPostingDetailsCostFromDto(
  dto: GetStockPostingDetailsCostDTO,
): GetStockPostingDetailsCost {
  return {
    id: dto.id,
    amount: dto.amount,
    currency: dto.currency,
    basisKind: dto.basis_kind,
    sourceSystem: dto.source_system,
    sourceReference: dto.source_reference,
    allocations: dto.allocations.map(getStockPostingDetailsAllocationFromDto),
  };
}
export function getStockPostingDetailsResultFromDto(
  dto: GetStockPostingDetailsResultDTO,
): GetStockPostingDetailsResult {
  return {
    id: dto.id,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    documentId: dto.document_id,
    documentVersionAtExecution: dto.document_version_at_execution,
    documentCurrentVersion: dto.document_current_version,
    documentCurrentStatus: dto.document_current_status,
    operationType: dto.operation_type,
    executedAt: dto.executed_at,
    postedAt: dto.posted_at,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    hasReceiptResult: dto.has_receipt_result,
    lines: dto.lines.map(getStockPostingDetailsLineFromDto),
    ledger: dto.ledger.map(getStockPostingDetailsEntryFromDto),
    costs: dto.costs.map(getStockPostingDetailsCostFromDto),
  };
}

export function listStockBalancesItemFromDto(
  dto: ListStockBalancesItemDTO,
): ListStockBalancesItem {
  return {
    key: dto.key,
    inventoryItemId: dto.inventory_item_id,
    sku: dto.sku,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    warehouseIsActive: dto.warehouse_is_active,
    locationId: dto.location_id,
    locationCode: dto.location_code,
    locationName: dto.location_name,
    locationIsActive: dto.location_is_active,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    lotId: dto.lot_id,
    lotNumber: dto.lot_number,
    serialId: dto.serial_id,
    serialNumber: dto.serial_number,
    stockStatus: dto.stock_status,
    baseUom: dto.base_uom,
    manufacturedOn: dto.manufactured_on,
    expiresOn: dto.expires_on,
    onHandQty: dto.on_hand_qty,
    positionCount: dto.position_count,
    lotCount: dto.lot_count,
    serialCount: dto.serial_count,
  };
}
export function listStockBalancesResultFromDto(
  dto: ListStockBalancesResultDTO,
): ListStockBalancesResult {
  return {
    items: dto.items.map(listStockBalancesItemFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
