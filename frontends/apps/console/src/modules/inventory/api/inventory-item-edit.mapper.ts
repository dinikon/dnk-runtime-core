import type { InventoryItemChanges } from "../model/inventory-item-editor.types.ts";
import type { PatchInventoryItemRequestDTO } from "./inventory-item-settings.dto.ts";
export function inventoryItemChangesToDto(
  value: InventoryItemChanges,
): PatchInventoryItemRequestDTO {
  const dto: PatchInventoryItemRequestDTO = {};
  if (value.sku !== undefined) dto.sku = value.sku;
  if (value.barcodes !== undefined) dto.barcodes = [...value.barcodes];
  if (value.baseUom !== undefined) dto.base_uom = value.baseUom;
  if (value.quantityStep !== undefined)
    dto.quantity_rules = { step: value.quantityStep.trim() };
  if (value.trackingMode !== undefined) dto.tracking_mode = value.trackingMode;
  if (value.expirationMode !== undefined)
    dto.expiration_mode = value.expirationMode;
  return dto;
}
