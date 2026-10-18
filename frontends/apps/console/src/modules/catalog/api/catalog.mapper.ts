import type {
  ReadItemDTO,
  ListItemDTO,
  UpdateItemRequest,
  DefaultSchemaResponse,
} from "./catalog.dto";
import type {
  CatalogItem,
  CatalogListItem,
  CatalogSchema,
} from "../model/catalog.types";
export function itemFromDto(value: ReadItemDTO): CatalogItem {
  return { ...value, title: value.content?.title ?? null };
}

export function listItemFromDto(value: ListItemDTO): CatalogListItem {
  return {
    id: value.id,

    status: value.status,
    sku: value.sku,
    title: value.title,
    price: value.price,
    currency: value.currency,
    availableForSale: value.available_for_sale,
  };
}

export function updateItemToDto(
  value: import("../model/product.types").ProductPatch,
): UpdateItemRequest {
  return { ...value };
}
export function schemaFromDto(value: DefaultSchemaResponse): CatalogSchema {
  return {
    locale: value.locale,
    schema: {
      ...value.schema,
      blocks: value.schema.blocks.map((block) => ({ ...block })),
    },
  };
}
