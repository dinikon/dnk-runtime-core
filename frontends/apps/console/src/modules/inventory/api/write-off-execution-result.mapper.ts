import type { GetWriteOffExecutionResultResponseDTO } from "./write-off-execution-result.dto";
import type { WriteOffExecutionResult } from "../model/write-off-execution-result.types";
export function writeOffExecutionResultFromDto(
  dto: GetWriteOffExecutionResultResponseDTO,
): WriteOffExecutionResult {
  return {
    documentId: dto.document_id,
    executionId: dto.execution_id,
    postingId: dto.posting_id,
    versionBefore: dto.document_version_before,
    versionAfter: dto.document_version_after,
    documentStatus: dto.document_status,
    reason: dto.reason,
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
