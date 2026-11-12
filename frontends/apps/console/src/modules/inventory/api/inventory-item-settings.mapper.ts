import type {
  InventoryItemDetails,
  InventoryItemSettings,
  InventoryUom,
} from "../model/inventory-item-settings.types.ts";
import type {
  GetInventoryItemResponseDTO,
  PatchInventoryItemSettingsRequestDTO,
  PatchInventoryItemSettingsResponseDTO,
  ListInventoryUomsResponseDTO,
} from "./inventory-item-settings.dto.ts";

export function inventoryItemDetailsFromDto(
  dto: GetInventoryItemResponseDTO | PatchInventoryItemSettingsResponseDTO,
): InventoryItemDetails {
  return {
    id: dto.id,
    sku: dto.sku,
    baseUom: dto.base_uom,
    quantityStep: dto.quantity_rules.step,
    trackingMode: dto.tracking_mode,
    expirationMode: dto.expiration_mode,
    barcodes: dto.barcodes.map((value) => ({ ...value })),
  };
}

export function inventoryItemSettingsToDto(
  value: InventoryItemSettings,
): PatchInventoryItemSettingsRequestDTO {
  return {
    base_uom: value.baseUom,
    quantity_rules: { step: value.quantityStep.trim() },
    tracking_mode: value.trackingMode,
    expiration_mode: value.expirationMode,
  };
}

export function inventoryUomsFromDto(
  dto: ListInventoryUomsResponseDTO,
): InventoryUom[] {
  return dto.items.map((item) => ({ ...item }));
}
