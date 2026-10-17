import type {
  GetAttributeResponse,
  ListAttributeItemDTO,
  ReadItemDTO,
} from "./catalog.dto";
import type {
  CatalogAttribute,
  CollectionItem,
  CatalogItem,
} from "../model/catalog.types";
export function attributeFromDto(d: GetAttributeResponse): CatalogAttribute {
  return {
    id: d.id,
    code: d.code,
    label: d.label,

    locales: d.locales,
    options: d.options,
  };
}
export function attributeItem(d: ListAttributeItemDTO): CollectionItem {
  return {
    id: d.id,
    label: d.label ?? d.code,
    description: `${d.code} · enum · Значений: ${d.option_count}`,

    system: false,
  };
}
export function categoryFromDto(
  d: import("./catalog.dto").ListCategoryItemDTO,
): import("../model/catalog.types").CatalogCategory {
  return {
    id: d.id,
    label: d.label,

    parentId: d.parent_id,
    childCount: d.child_count,
  };
}
export function tagFromDto(
  d: import("./catalog.dto").ListTagItemDTO,
): import("../model/catalog.types").CatalogTag {
  return { id: d.id, label: d.label };
}
export function tagItem(
  d: import("./catalog.dto").ListTagItemDTO,
): CollectionItem {
  return {
    id: d.id,
    label: d.label ?? `Метка ${d.id}`,
    description: "Метка",

    system: false,
  };
}

export function itemFromDto(value: ReadItemDTO): CatalogItem {
  return { ...value, title: value.content?.name ?? null };
}

export function listItemFromDto(value: import("./catalog.dto").ListItemDTO) {
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
