import type {
  CatalogSkuSelection,
  SetCatalogSkuResult,
} from "../model/catalog-sku.types.ts";
import type {
  SetCatalogSkuRequestDTO,
  SetCatalogSkuResponseDTO,
} from "./catalog-sku.dto.ts";

export function catalogSkuSelectionToDto(
  value: CatalogSkuSelection,
): SetCatalogSkuRequestDTO {
  if (value.mode === "existing")
    return { mode: "existing", inventory_item_id: value.inventoryItemId };
  if (value.mode === "create") return { mode: "create", sku: value.sku };
  return { mode: "clear" };
}

export function setCatalogSkuResultFromDto(
  value: SetCatalogSkuResponseDTO,
): SetCatalogSkuResult {
  return {
    itemId: value.item_id,
    inventoryItemId: value.inventory_item_id,
    sku: value.sku,
    inventoryItemCreated: value.inventory_item_created,
  };
}
