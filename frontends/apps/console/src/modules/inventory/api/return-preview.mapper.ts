import type { ReturnPreviewResponseDTO } from "./return-preview.dto";
import type { ReturnPreview } from "../model/return-preview.types";
export function returnPreviewFromDto(
  dto: ReturnPreviewResponseDTO,
): ReturnPreview {
  return {
    documentId: dto.document_id,
    version: dto.version,
    reason: dto.reason,
    direction: dto.direction,
    originExecutionId: dto.origin_execution_id,
    positions: dto.positions.map((v) => ({
      id: v.id,
      exists: v.exists,
      role: v.role,
      inventoryItemId: v.inventory_item_id,
      sku: v.sku,
      locationCode: v.location_code,
      stockStatus: v.stock_status,
      lotNumber: v.lot_number,
      serialNumber: v.serial_number,
      baseUom: v.base_uom,
      before: v.before_quantity,
      delta: v.delta,
      after: v.after_quantity,
    })),
  };
}
