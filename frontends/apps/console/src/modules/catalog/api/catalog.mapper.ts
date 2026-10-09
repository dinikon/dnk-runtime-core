import type {
  GetProductResponse,
  GetProductTypeResponse,
  GetContentBlockResponse,
} from "./catalog.dto";
import type {
  Product,
  ProductType,
  ContentBlock,
  CollectionItem,
} from "../model/catalog.types";
export function productFromDto(d: GetProductResponse): Product {
  return {
    id: d.id,
    kind: d.kind,
    typeId: d.product_type_id,
    revision: d.revision,
    schemaVersion: d.schema_version,
    content: d.content,
    locales: d.locales,
    variantId: d.variant_id,
    virtual: d.virtual,
    downloadable: d.downloadable,
    variantContent: d.variant_content,
    variantLocales: d.variant_locales,
  };
}
export function typeFromDto(d: GetProductTypeResponse): ProductType {
  return {
    id: d.id,
    code: d.code,
    label: d.label,
    system: d.is_system,
    revision: d.revision,
    schemaVersion: d.schema_version,
    locales: d.locales,
    blocks: d.blocks.map((b) => ({
      blockId: b.block_id,
      code: b.code,
      label: b.label,
      valueType: b.value_type,
      scope: b.scope,
      required: b.required,
      position: b.position,
    })),
  };
}
export function blockFromDto(d: GetContentBlockResponse): ContentBlock {
  return {
    id: d.id,
    code: d.code,
    label: d.label,
    system: d.is_system,
    revision: d.revision,
    valueType: d.value_type,
    locales: d.locales,
  };
}
export function productItem(d: GetProductResponse): CollectionItem {
  return {
    id: d.id,
    label:
      d.content?.["c0000000-0000-4000-8000-000000000002"] ?? `Товар ${d.id}`,
    description: d.virtual
      ? "SIMPLE · Виртуальная позиция"
      : "SIMPLE · Физическая позиция",
    revision: d.revision,
    system: false,
  };
}
export function typeItem(d: GetProductTypeResponse): CollectionItem {
  return {
    id: d.id,
    label: d.label ?? d.code,
    description: `${d.code} · Схема ${d.schema_version}`,
    revision: d.revision,
    system: d.is_system,
  };
}
export function blockItem(d: GetContentBlockResponse): CollectionItem {
  return {
    id: d.id,
    label: d.label ?? d.code,
    description: `${d.code} · ${d.value_type}`,
    revision: d.revision,
    system: d.is_system,
  };
}
