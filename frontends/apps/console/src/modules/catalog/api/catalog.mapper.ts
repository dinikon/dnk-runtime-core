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
    revision: d.revision,
    locales: d.locales,
    options: d.options,
  };
}
export function attributeItem(d: ListAttributeItemDTO): CollectionItem {
  return {
    id: d.id,
    label: d.label ?? d.code,
    description: `${d.code} · enum · Значений: ${d.option_count}`,
    revision: d.revision,
    system: false,
  };
}
export function categoryFromDto(
  d: import("./catalog.dto").ListCategoryItemDTO,
): import("../model/catalog.types").CatalogCategory {
  return {
    id: d.id,
    label: d.label,
    revision: d.revision,
    parentId: d.parent_id,
    childCount: d.child_count,
  };
}
export function tagFromDto(
  d: import("./catalog.dto").ListTagItemDTO,
): import("../model/catalog.types").CatalogTag {
  return { id: d.id, label: d.label, revision: d.revision };
}
export function tagItem(
  d: import("./catalog.dto").ListTagItemDTO,
): CollectionItem {
  return {
    id: d.id,
    label: d.label ?? `Метка ${d.id}`,
    description: "Метка",
    revision: d.revision,
    system: false,
  };
}

export function itemFromDto(value: ReadItemDTO): CatalogItem {
  return {
    id: value.own.id,
    rootId: value.root_id,
    rootRevision: value.root_revision,
    kind: value.own.kind,
    title: value.effective.content?.name ?? null,
    own: value.own,
    effective: value.effective,
    stockStatus: value.stock_status,
    priceMin: value.price_min,
    priceMax: value.price_max,
    priceIncomplete: value.price_incomplete,
  };
}

export function listItemFromDto(value: import("./catalog.dto").ListItemDTO) {
  return {
    id: value.id,
    kind: value.kind,
    rootRevision: value.root_revision,
    status: value.status,
    sku: value.sku,
    title: value.title,
    price: value.price,
    currency: value.currency,
    priceMin: value.price_min,
    priceMax: value.price_max,
    priceIncomplete: value.price_incomplete,
  };
}
