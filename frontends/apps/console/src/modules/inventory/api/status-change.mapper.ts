import type { StatusChangeEditValues } from "../model/status-change.types";
import type { PatchStatusChangeDocumentRequestDTO } from "./status-change.dto";
import type {
  GetStatusChangeDocumentResponseDTO,
  ListStatusChangeDocumentsResponseDTO,
  CreateStatusChangeDraftRequestDTO,
  StatusChangeListItemResponseDTO,
} from "./status-change.dto";
import type {
  StatusChangeDocument,
  StatusChangeListItem,
  StatusChangesPage,
  StatusChangesParams,
  StatusChangeDraftValues,
} from "../model/status-change.types";
import { normalizeStatusChangeQuantity } from "../model/status-change-draft.ts";
export function statusChangeFromDto(
  dto: GetStatusChangeDocumentResponseDTO,
): StatusChangeDocument {
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
    targetStatus: dto.target_status,
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
export function statusChangeListItemFromDto(
  dto: StatusChangeListItemResponseDTO,
): StatusChangeListItem {
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
    targetStatus: dto.target_status,
    sourceSystem: dto.source_system,
    sourceReference: dto.source_reference,
    sourceVersion: dto.source_version,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    version: dto.version,
    lineCount: dto.line_count,
  };
}
export function statusChangesPageFromDto(
  dto: ListStatusChangeDocumentsResponseDTO,
): StatusChangesPage {
  return { ...dto, items: dto.items.map(statusChangeListItemFromDto) };
}
export function createStatusChangeToDto(
  v: StatusChangeDraftValues,
): CreateStatusChangeDraftRequestDTO {
  return {
    warehouse_id: v.warehouseId,
    owner_id: v.ownerId,
    reason: v.reason.trim(),
    target_status: v.targetStatus,
    lines: v.lines.map((l) => ({
      inventory_item_id: l.inventoryItemId,
      quantity: normalizeStatusChangeQuantity(l.quantity),
      uom: l.uom,
    })),
  };
}
export function statusChangesParamsToDto(
  p: StatusChangesParams,
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

export function patchStatusChangeToDto(
  values: StatusChangeEditValues,
): PatchStatusChangeDocumentRequestDTO {
  return {
    expected_version: values.expectedVersion,
    reason: values.reason.trim(),
    target_status: values.targetStatus,
    lines: values.lines.map((line) =>
      line.id
        ? {
            id: line.id,
            quantity: normalizeStatusChangeQuantity(line.quantity),
            uom: line.uom,
          }
        : {
            inventory_item_id: line.inventoryItemId,
            quantity: normalizeStatusChangeQuantity(line.quantity),
            uom: line.uom,
          },
    ),
  };
}
