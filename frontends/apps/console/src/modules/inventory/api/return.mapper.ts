import type { ReturnEditValues } from "../model/return.types";
import type { PatchReturnDocumentRequestDTO } from "./return.dto";
import type {
  GetReturnDocumentResponseDTO,
  ListReturnDocumentsResponseDTO,
  CreateReturnDraftRequestDTO,
  ReturnListItemResponseDTO,
} from "./return.dto";
import type {
  ReturnDocument,
  ReturnListItem,
  ReturnsPage,
  ReturnsParams,
  ReturnDraftValues,
} from "../model/return.types";
import { normalizeReturnQuantity } from "../model/return-draft.ts";
export function returnFromDto(
  dto: GetReturnDocumentResponseDTO,
): ReturnDocument {
  return {
    id: dto.id,
    operationType: dto.operation_type,
    status: dto.status,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    reason: dto.reason,
    direction: dto.direction,
    originExecutionId: dto.origin_execution_id,
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
      originExecutionLineId: l.origin_execution_line_id,
    })),
  };
}
export function returnListItemFromDto(
  dto: ReturnListItemResponseDTO,
): ReturnListItem {
  return {
    id: dto.id,
    operationType: dto.operation_type,
    status: dto.status,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    ownerName: dto.owner_name,
    reason: dto.reason,
    direction: dto.direction,
    originExecutionId: dto.origin_execution_id,
    sourceSystem: dto.source_system,
    sourceReference: dto.source_reference,
    sourceVersion: dto.source_version,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    version: dto.version,
    lineCount: dto.line_count,
  };
}
export function returnsPageFromDto(
  dto: ListReturnDocumentsResponseDTO,
): ReturnsPage {
  return { ...dto, items: dto.items.map(returnListItemFromDto) };
}
export function createReturnToDto(
  v: ReturnDraftValues,
): CreateReturnDraftRequestDTO {
  return {
    origin_execution_id: v.originExecutionId,
    reason: v.reason.trim(),
    lines: v.lines.map((l) => ({
      origin_execution_line_id: l.originExecutionLineId,
      quantity: normalizeReturnQuantity(l.quantity),
      uom: l.uom,
    })),
  };
}
export function returnsParamsToDto(
  p: ReturnsParams,
): Record<string, string | number | undefined> {
  return {
    search: p.search.trim() || undefined,
    warehouse_id: p.warehouseId,
    owner_id: p.ownerId,
    status: p.status,
    origin_execution_id: p.originExecutionId,
    created_from: p.createdFrom,
    created_to: p.createdTo,
    offset: p.offset,
    limit: p.limit,
  };
}

export function patchReturnToDto(
  values: ReturnEditValues,
): PatchReturnDocumentRequestDTO {
  return {
    expected_version: values.expectedVersion,
    reason: values.reason.trim(),
    lines: values.lines.map((line) =>
      line.id
        ? {
            id: line.id,
            quantity: normalizeReturnQuantity(line.quantity),
            uom: line.uom,
          }
        : {
            origin_execution_line_id: line.originExecutionLineId,
            quantity: normalizeReturnQuantity(line.quantity),
            uom: line.uom,
          },
    ),
  };
}
