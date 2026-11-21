import type {
  PrepareReturnResponseDTO,
  ListReturnSourcesResponseDTO,
  ListReturnExecutionsResponseDTO,
  PostReturnRequestDTO,
  PostReturnResponseDTO,
} from "./return-posting.dto";
import type {
  ReturnPreparation,
  ReturnSources,
  ReturnExecutionHistory,
  ReturnExecutionValues,
  ReturnPostingResult,
} from "../model/return-posting.types";
import { quantityText } from "../model/stock-quantity-text.ts";
export function returnPreparationFromDto(
  dto: PrepareReturnResponseDTO,
): ReturnPreparation {
  return {
    documentId: dto.document_id,
    version: dto.version,
    status: dto.status,
    warehouseId: dto.warehouse_id,
    reason: dto.reason,
    direction: dto.direction,
    originExecutionId: dto.origin_execution_id,
    lines: dto.lines.map((v) => ({
      documentLineId: v.document_line_id,
      originExecutionLineId: v.origin_execution_line_id,
      originalQuantity: v.original_quantity,
      returnedQuantity: v.returned_quantity,
      returnableQuantity: v.returnable_quantity,
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
export function returnSourcesFromDto(
  dto: ListReturnSourcesResponseDTO,
): ReturnSources {
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
export function returnHistoryFromDto(
  dto: ListReturnExecutionsResponseDTO,
): ReturnExecutionHistory {
  return {
    ...dto,
    items: dto.items.map((v) => ({
      executionId: v.execution_id,
      postingId: v.posting_id,
      postedAt: v.posted_at,
      documentVersionAfter: v.document_version_after,
      documentStatus: v.document_status,
      reason: v.reason,
      direction: v.direction,
      originExecutionId: v.origin_execution_id,
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
export function returnExecutionToDto(
  values: ReturnExecutionValues,
): PostReturnRequestDTO {
  return {
    expected_version: values.expectedVersion,
    lines: values.rows
      .filter((v) => v.selected)
      .map((v) => ({
        client_line_id: v.key,
        document_line_id: v.documentLineId,
        ...(v.direction === "FROM_RECIPIENT"
          ? {
              location_id: v.destination?.id ?? "",
              stock_status: v.stockStatus,
            }
          : { source_position_id: v.source?.id ?? "" }),
        quantity: quantityText(v.quantity),
        uom: v.uom,
      })),
  };
}
export function returnResultFromDto(
  dto: PostReturnResponseDTO,
): ReturnPostingResult {
  return {
    documentId: dto.document_id,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    documentVersionAfter: dto.document_version_after,
    documentStatus: dto.document_status,
    originExecutionId: dto.origin_execution_id,
  };
}

export function returnDestinationsFromDto(
  dto: import("./return-posting.dto").ListReturnDestinationsResponseDTO,
): import("../model/return-posting.types").ReturnDestinations {
  return {
    items: dto.items.map((item) => ({
      id: item.id,
      code: item.code,
      name: item.name,
    })),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}
