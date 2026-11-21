import type {
  InventoryItemListRowDTO,
  ListInventoryItemsRequestDTO,
  ListInventoryItemsResponseDTO,
} from "./inventory-item.dto.ts";
import type {
  InventoryItemListRow,
  InventoryItemsListParams,
  InventoryItemsPage,
} from "../model/inventory-item.types.ts";

export function inventoryItemFromDto(
  dto: InventoryItemListRowDTO,
): InventoryItemListRow {
  return {
    id: dto.id,
    sku: dto.sku,
    baseUom: dto.base_uom,
    quantityStep: dto.quantity_rules.step,
    trackingMode: dto.tracking_mode,
    expirationMode: dto.expiration_mode,
  };
}

export function inventoryItemsPageFromDto(
  dto: ListInventoryItemsResponseDTO,
): InventoryItemsPage {
  return {
    items: dto.items.map(inventoryItemFromDto),
    total: dto.total,
    offset: dto.offset,
    limit: dto.limit,
  };
}

export function inventoryItemsParamsToDto(
  params: InventoryItemsListParams,
): ListInventoryItemsRequestDTO {
  return {
    search: params.search || undefined,
    offset: params.offset,
    limit: params.limit,
  };
}
