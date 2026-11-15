import type { WriteOffEditValues } from "../model/write-off.types";
import type { PatchWriteOffDocumentRequestDTO } from "./write-off.dto";
import type {
  GetWriteOffDocumentResponseDTO,
  ListWriteOffDocumentsResponseDTO,
  CreateWriteOffDraftRequestDTO,
  WriteOffListItemResponseDTO,
} from "./write-off.dto";
import type {
  WriteOffDocument,
  WriteOffListItem,
  WriteOffsPage,
  WriteOffsParams,
  WriteOffDraftValues,
} from "../model/write-off.types";
import { normalizeWriteOffQuantity } from "../model/write-off-draft.ts";
export function writeOffFromDto(
  dto: GetWriteOffDocumentResponseDTO,
): WriteOffDocument {
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
export function writeOffListItemFromDto(
  dto: WriteOffListItemResponseDTO,
): WriteOffListItem {
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
    sourceSystem: dto.source_system,
    sourceReference: dto.source_reference,
    sourceVersion: dto.source_version,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    version: dto.version,
    lineCount: dto.line_count,
  };
}
export function writeOffsPageFromDto(
  dto: ListWriteOffDocumentsResponseDTO,
): WriteOffsPage {
  return { ...dto, items: dto.items.map(writeOffListItemFromDto) };
}
export function createWriteOffToDto(
  v: WriteOffDraftValues,
): CreateWriteOffDraftRequestDTO {
  return {
    warehouse_id: v.warehouseId,
    owner_id: v.ownerId,
    reason: v.reason.trim(),
    lines: v.lines.map((l) => ({
      inventory_item_id: l.inventoryItemId,
      quantity: normalizeWriteOffQuantity(l.quantity),
      uom: l.uom,
    })),
  };
}
export function writeOffsParamsToDto(
  p: WriteOffsParams,
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

export function patchWriteOffToDto(
  values: WriteOffEditValues,
): PatchWriteOffDocumentRequestDTO {
  return {
    expected_version: values.expectedVersion,
    reason: values.reason.trim(),
    lines: values.lines.map((line) =>
      line.id
        ? {
            id: line.id,
            quantity: normalizeWriteOffQuantity(line.quantity),
            uom: line.uom,
          }
        : {
            inventory_item_id: line.inventoryItemId,
            quantity: normalizeWriteOffQuantity(line.quantity),
            uom: line.uom,
          },
    ),
  };
}
