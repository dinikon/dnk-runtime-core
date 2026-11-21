import type {
  InventoryItemDetails,
  InventoryUom,
} from "../model/inventory-item-settings.types.ts";
import type {
  GetInventoryItemResponseDTO,
  PatchInventoryItemResponseDTO,
  ListInventoryUomsResponseDTO,
} from "./inventory-item-settings.dto.ts";

export function inventoryItemDetailsFromDto(
  dto: GetInventoryItemResponseDTO | PatchInventoryItemResponseDTO,
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

export function inventoryUomsFromDto(
  dto: ListInventoryUomsResponseDTO,
): InventoryUom[] {
  return dto.items.map((item) => ({ ...item }));
}
