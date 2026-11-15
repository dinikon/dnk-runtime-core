import type {
  PrepareWriteOffResponseDTO,
  ListWriteOffSourcesResponseDTO,
  ListWriteOffExecutionsResponseDTO,
  PostWriteOffRequestDTO,
  PostWriteOffResponseDTO,
} from "./write-off-posting.dto";
import type {
  WriteOffPreparation,
  WriteOffSources,
  WriteOffExecutionHistory,
  WriteOffExecutionValues,
  WriteOffPostingResult,
} from "../model/write-off-posting.types";
import { quantityText } from "../model/stock-quantity-text.ts";
export function writeOffPreparationFromDto(
  dto: PrepareWriteOffResponseDTO,
): WriteOffPreparation {
  return {
    documentId: dto.document_id,
    version: dto.version,
    status: dto.status,
    warehouseId: dto.warehouse_id,
    reason: dto.reason,
    lines: dto.lines.map((v) => ({
      documentLineId: v.document_line_id,
      position: v.position,
      inventoryItemId: v.inventory_item_id,
      sku: v.sku,
      baseUom: v.base_uom,
      currentBaseUom: v.current_base_uom,
      plannedQuantity: v.planned_quantity,
      executedQuantity: v.executed_quantity,
      remainingQuantity: v.remaining_quantity,
      quantityStep: v.quantity_step,
      trackingMode: v.tracking_mode,
      expirationMode: v.expiration_mode,
    })),
  };
}
export function writeOffSourcesFromDto(
  dto: ListWriteOffSourcesResponseDTO,
): WriteOffSources {
  return {
    ...dto,
    items: dto.items.map((v) => ({
      id: v.id,
      inventoryItemId: v.inventory_item_id,
      locationId: v.location_id,
      locationCode: v.location_code,
      stockStatus: v.stock_status,
      lotId: v.lot_id,
      lotNumber: v.lot_number,
      serialId: v.serial_id,
      serialNumber: v.serial_number,
      manufacturedOn: v.manufactured_on,
      expiresOn: v.expires_on,
      baseUom: v.base_uom,
      onHandQuantity: v.on_hand_quantity,
      version: v.version,
    })),
  };
}
export function writeOffHistoryFromDto(
  dto: ListWriteOffExecutionsResponseDTO,
): WriteOffExecutionHistory {
  return {
    ...dto,
    items: dto.items.map((v) => ({
      executionId: v.execution_id,
      postingId: v.posting_id,
      postedAt: v.posted_at,
      documentVersionAfter: v.document_version_after,
      documentStatus: v.document_status,
      reason: v.reason,
      lineCount: v.line_count,
      lines: v.lines.map((l) => ({
        documentLineId: l.document_line_id,
        position: l.position,
        sku: l.sku,
        baseUom: l.base_uom,
        quantity: l.quantity,
        allocationCount: l.allocation_count,
      })),
    })),
  };
}
export function writeOffExecutionToDto(
  values: WriteOffExecutionValues,
): PostWriteOffRequestDTO {
  return {
    expected_version: values.expectedVersion,
    lines: values.rows
      .filter((v) => v.selected)
      .map((v) => ({
        client_line_id: v.key,
        document_line_id: v.documentLineId,
        source_position_id: v.source?.id ?? "",
        quantity: quantityText(v.quantity),
        uom: v.uom,
      })),
  };
}
export function writeOffResultFromDto(
  dto: PostWriteOffResponseDTO,
): WriteOffPostingResult {
  return {
    documentId: dto.document_id,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    documentVersionAfter: dto.document_version_after,
    documentStatus: dto.document_status,
  };
}
