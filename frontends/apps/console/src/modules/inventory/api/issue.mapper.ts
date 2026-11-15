import type { IssueEditValues } from "../model/issue.types";
import type { PatchIssueDocumentRequestDTO } from "./issue.dto";
import type {
  GetIssueDocumentResponseDTO,
  ListIssueDocumentsResponseDTO,
  CreateIssueDraftRequestDTO,
  IssueListItemResponseDTO,
} from "./issue.dto";
import type {
  IssueDocument,
  IssueListItem,
  IssuesPage,
  IssuesParams,
  IssueDraftValues,
} from "../model/issue.types";
import { normalizeIssueQuantity } from "../model/issue-draft.ts";
export function issueFromDto(dto: GetIssueDocumentResponseDTO): IssueDocument {
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
export function issueListItemFromDto(
  dto: IssueListItemResponseDTO,
): IssueListItem {
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
export function issuesPageFromDto(
  dto: ListIssueDocumentsResponseDTO,
): IssuesPage {
  return { ...dto, items: dto.items.map(issueListItemFromDto) };
}
export function createIssueToDto(
  v: IssueDraftValues,
): CreateIssueDraftRequestDTO {
  return {
    warehouse_id: v.warehouseId,
    owner_id: v.ownerId,
    lines: v.lines.map((l) => ({
      inventory_item_id: l.inventoryItemId,
      quantity: normalizeIssueQuantity(l.quantity),
      uom: l.uom,
    })),
  };
}
export function issuesParamsToDto(
  p: IssuesParams,
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

export function patchIssueToDto(
  values: IssueEditValues,
): PatchIssueDocumentRequestDTO {
  return {
    expected_version: values.expectedVersion,
    lines: values.lines.map((line) =>
      line.id
        ? {
            id: line.id,
            quantity: normalizeIssueQuantity(line.quantity),
            uom: line.uom,
          }
        : {
            inventory_item_id: line.inventoryItemId,
            quantity: normalizeIssueQuantity(line.quantity),
            uom: line.uom,
          },
    ),
  };
}
