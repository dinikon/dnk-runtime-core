import type { InternalMoveEditValues } from "../model/internal-move.types";
import type { PatchInternalMoveDocumentRequestDTO } from "./internal-move.dto";
import type {
  GetInternalMoveDocumentResponseDTO,
  ListInternalMoveDocumentsResponseDTO,
  CreateInternalMoveDraftRequestDTO,
  InternalMoveListItemResponseDTO,
} from "./internal-move.dto";
import type {
  InternalMoveDocument,
  InternalMoveListItem,
  InternalMovesPage,
  InternalMovesParams,
  InternalMoveDraftValues,
} from "../model/internal-move.types";
import { normalizeInternalMoveQuantity } from "../model/internal-move-draft.ts";
export function internalMoveFromDto(
  dto: GetInternalMoveDocumentResponseDTO,
): InternalMoveDocument {
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
export function internalMoveListItemFromDto(
  dto: InternalMoveListItemResponseDTO,
): InternalMoveListItem {
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
export function internalMovesPageFromDto(
  dto: ListInternalMoveDocumentsResponseDTO,
): InternalMovesPage {
  return { ...dto, items: dto.items.map(internalMoveListItemFromDto) };
}
export function createInternalMoveToDto(
  v: InternalMoveDraftValues,
): CreateInternalMoveDraftRequestDTO {
  return {
    warehouse_id: v.warehouseId,
    owner_id: v.ownerId,
    lines: v.lines.map((l) => ({
      inventory_item_id: l.inventoryItemId,
      quantity: normalizeInternalMoveQuantity(l.quantity),
      uom: l.uom,
    })),
  };
}
export function internalMovesParamsToDto(
  p: InternalMovesParams,
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

export function patchInternalMoveToDto(
  values: InternalMoveEditValues,
): PatchInternalMoveDocumentRequestDTO {
  return {
    expected_version: values.expectedVersion,
    lines: values.lines.map((line) =>
      line.id
        ? {
            id: line.id,
            quantity: normalizeInternalMoveQuantity(line.quantity),
            uom: line.uom,
          }
        : {
            inventory_item_id: line.inventoryItemId,
            quantity: normalizeInternalMoveQuantity(line.quantity),
            uom: line.uom,
          },
    ),
  };
}
