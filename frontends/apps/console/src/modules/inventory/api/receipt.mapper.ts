import type { ReceiptEditValues } from "../model/receipt.types";
import type { PatchReceiptDocumentRequestDTO } from "./receipt.dto";
import type {
  GetReceiptDocumentResponseDTO,
  ListReceiptDocumentsResponseDTO,
  CreateReceiptDraftRequestDTO,
  ReceiptListItemResponseDTO,
} from "./receipt.dto";
import type {
  ReceiptDocument,
  ReceiptListItem,
  ReceiptsPage,
  ReceiptsParams,
  ReceiptDraftValues,
} from "../model/receipt.types";
import { normalizeReceiptQuantity } from "../model/receipt-draft.ts";
export function receiptFromDto(
  dto: GetReceiptDocumentResponseDTO,
): ReceiptDocument {
  return {
    id: dto.id,
    operationType: dto.operation_type,
    status: dto.status,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    sourceSystem: dto.source_system,
    sourceReference: dto.source_reference,
    sourceVersion: dto.source_version,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    version: dto.version,
    lines: dto.lines.map((l) => ({
      id: l.id,
      position: l.position,
      inventoryItemId: l.inventory_item_id,
      sku: l.sku,
      baseUom: l.base_uom,
      plannedQty: l.planned_qty,
      sourceQuantity: l.source_quantity,
      sourceUom: l.source_uom,
      factorToBase: l.factor_to_base,
      executedQty: l.executed_qty,
      remainingQty: l.remaining_qty,
    })),
  };
}
export function receiptListItemFromDto(
  dto: ReceiptListItemResponseDTO,
): ReceiptListItem {
  return {
    id: dto.id,
    operationType: dto.operation_type,
    status: dto.status,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    sourceSystem: dto.source_system,
    sourceReference: dto.source_reference,
    sourceVersion: dto.source_version,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    version: dto.version,
    lineCount: dto.line_count,
  };
}
export function receiptsPageFromDto(
  dto: ListReceiptDocumentsResponseDTO,
): ReceiptsPage {
  return { ...dto, items: dto.items.map(receiptListItemFromDto) };
}
export function createReceiptToDto(
  v: ReceiptDraftValues,
): CreateReceiptDraftRequestDTO {
  return {
    warehouse_id: v.warehouseId,
    owner_id: v.ownerId,
    lines: v.lines.map((l) => ({
      inventory_item_id: l.inventoryItemId,
      quantity: normalizeReceiptQuantity(l.quantity),
      uom: l.uom,
    })),
  };
}
export function receiptsParamsToDto(
  p: ReceiptsParams,
): Record<string, string | number | undefined> {
  return {
    search: p.search.trim() || undefined,
    warehouse_id: p.warehouseId,
    owner_id: p.ownerId,
    status: p.status,
    created_from: p.createdFrom,
    created_to: p.createdTo,
    offset: p.offset,
    limit: p.limit,
  };
}

export function patchReceiptToDto(
  values: ReceiptEditValues,
): PatchReceiptDocumentRequestDTO {
  return {
    expected_version: values.expectedVersion,
    lines: values.lines.map((line) =>
      line.id
        ? {
            id: line.id,
            quantity: normalizeReceiptQuantity(line.quantity),
            uom: line.uom,
          }
        : {
            inventory_item_id: line.inventoryItemId,
            quantity: normalizeReceiptQuantity(line.quantity),
            uom: line.uom,
          },
    ),
  };
}
