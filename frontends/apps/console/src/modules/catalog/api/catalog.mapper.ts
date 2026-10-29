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
  return {
    ...value,
    title: value.effective_content?.title ?? value.content?.title ?? null,
  };
}

export function listItemFromDto(value: ListItemDTO): CatalogListItem {
  return {
    id: value.id,
    kind: value.kind,
    parent_id: value.parent_id,
    variant_count: value.variant_count,
    min_price: value.min_price,
    max_price: value.max_price,
    mixed_currencies: value.mixed_currencies,
    status: value.status,
    sku: value.sku,
    title: value.title,
    price: value.price,
    currency: value.currency,
    availableForSale: value.available_for_sale,
    stockStatus:
      value.stock_status === "in_stock" ||
      value.stock_status === "out_of_stock" ||
      value.stock_status === "on_backorder"
        ? value.stock_status
        : null,
    primaryImage: value.primary_image,
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
