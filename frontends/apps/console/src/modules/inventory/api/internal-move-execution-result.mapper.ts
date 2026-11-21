import type { GetInternalMoveExecutionResultResponseDTO } from "./internal-move-execution-result.dto";
import type { InternalMoveExecutionResult } from "../model/internal-move-execution-result.types";
export function internalMoveExecutionResultFromDto(
  dto: GetInternalMoveExecutionResultResponseDTO,
): InternalMoveExecutionResult {
  return {
    documentId: dto.document_id,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    versionBefore: dto.document_version_before,
    versionAfter: dto.document_version_after,
    documentStatus: dto.document_status,
    lines: dto.lines.map((v) => ({
      id: v.id,
      sku: v.sku,
      sourceQuantity: v.source_quantity,
      sourceUom: v.source_uom,
      quantity: v.quantity,
      baseUom: v.base_uom,
      locationCode: v.location_code,
      destinationLocationId: v.destination_location_id,
      destinationLocationCode: v.destination_location_code,
      lotNumber: v.lot_number,
      serialNumber: v.serial_number,
      positionId: v.position_id,
      destinationPositionId: v.destination_position_id,
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
