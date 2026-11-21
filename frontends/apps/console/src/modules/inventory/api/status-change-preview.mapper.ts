import type {
  StatusChangePreviewResponseDTO,
  StatusTransitionsResponseDTO,
} from "./status-change-preview.dto";
import type {
  StatusChangePreview,
  StatusTransition,
} from "../model/status-change-preview.types";
export function statusTransitionsFromDto(
  dto: StatusTransitionsResponseDTO,
): StatusTransition[] {
  return dto.items.map((v) => ({
    sourceStatus: v.source_status,
    targetStatuses: [...v.target_statuses],
  }));
}
export function statusChangePreviewFromDto(
  dto: StatusChangePreviewResponseDTO,
): StatusChangePreview {
  return {
    documentId: dto.document_id,
    version: dto.version,
    reason: dto.reason,
    targetStatus: dto.target_status,
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
