import type { ReturnOriginResponseDTO } from "./return-origin.dto";
import type { ReturnOrigin } from "../model/return-origin.types";
export function returnOriginFromDto(
  dto: ReturnOriginResponseDTO,
): ReturnOrigin {
  return {
    executionId: dto.execution_id,
    documentId: dto.document_id,
    operationType: dto.operation_type,
    direction: dto.direction,
    warehouseId: dto.warehouse_id,
    warehouseCode: dto.warehouse_code,
    warehouseName: dto.warehouse_name,
    ownerId: dto.owner_id,
    lines: dto.lines.map((v) => ({
      id: v.id,
      position: v.position,
      inventoryItemId: v.inventory_item_id,
      sku: v.sku,
      baseUom: v.base_uom,
      quantity: v.quantity,
      returnedQuantity: v.returned_quantity,
      remainingQuantity: v.remaining_quantity,
      locationId: v.location_id,
      locationCode: v.location_code,
      stockStatus: v.stock_status,
      lotId: v.lot_id,
      lotNumber: v.lot_number,
      serialId: v.serial_id,
      serialNumber: v.serial_number,
    })),
  };
}
