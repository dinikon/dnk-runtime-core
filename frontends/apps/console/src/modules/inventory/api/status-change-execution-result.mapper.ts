import type { GetStatusChangeExecutionResultResponseDTO } from "./status-change-execution-result.dto";
import type { StatusChangeExecutionResult } from "../model/status-change-execution-result.types";
export function statusChangeExecutionResultFromDto(
  dto: GetStatusChangeExecutionResultResponseDTO,
): StatusChangeExecutionResult {
  return {
    documentId: dto.document_id,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    versionBefore: dto.document_version_before,
    versionAfter: dto.document_version_after,
    documentStatus: dto.document_status,
    reason: dto.reason,
    targetStatus: dto.target_status,
    lines: dto.lines.map((v) => ({
      id: v.id,
      sku: v.sku,
      sourceQuantity: v.source_quantity,
      sourceUom: v.source_uom,
      quantity: v.quantity,
      baseUom: v.base_uom,
      locationCode: v.location_code,
      lotNumber: v.lot_number,
      serialNumber: v.serial_number,
      positionId: v.position_id,
      stockStatus: v.stock_status,
      destinationStockStatus: v.destination_stock_status,
      sourceLedgerEntryId: v.ledger_entry_id,
      destinationLedgerEntryId: v.destination_ledger_entry_id,
    })),
    positions: dto.positions.map((v) => ({
      id: v.id,
      baseUom: v.base_uom,
      before: v.before_quantity,
      delta: v.delta,
      after: v.after_quantity,
      beforeVersion: v.before_version,
      afterVersion: v.after_version,
    })),
  };
}
