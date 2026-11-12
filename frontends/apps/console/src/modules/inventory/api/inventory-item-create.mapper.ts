import type { CreateInventoryItemValues } from "../model/inventory-item-create.types.ts";
import type { InventoryItemDetails } from "../model/inventory-item-settings.types.ts";
import type {
  CreateInventoryItemRequestDTO,
  CreateInventoryItemResponseDTO,
} from "./inventory-item-create.dto.ts";

export function inventoryItemCreateToDto(
  value: CreateInventoryItemValues,
): CreateInventoryItemRequestDTO {
  return { sku: value.sku.trim() };
}

export function inventoryItemCreatedFromDto(
  dto: CreateInventoryItemResponseDTO,
): InventoryItemDetails {
  return {
    id: dto.id,
    sku: dto.sku,
    baseUom: dto.base_uom,
    quantityStep: dto.quantity_rules.step,
    trackingMode: dto.tracking_mode,
    expirationMode: dto.expiration_mode,
    barcodes: dto.barcodes.map((barcode) => ({ ...barcode })),
  };
}
