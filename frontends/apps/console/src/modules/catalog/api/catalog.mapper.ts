import type {
  GetProductResponse,
  GetProductTypeResponse,
  GetContentBlockResponse,
  ProductListItemDTO,
  GetAttributeResponse,
  ListAttributeItemDTO,
  GetVariantResponse,
  VariableStructureDTO,
  SimpleStructureDTO,
} from "./catalog.dto";
import type {
  Product,
  ProductType,
  ContentBlock,
  CollectionItem,
  CatalogAttribute,
  ProductVariant,
  ProductStructureDraft,
} from "../model/catalog.types";
export function productFromDto(d: GetProductResponse): Product {
  return {
    id: d.id,
    attributeValues: d.attribute_values.map((v) => ({
      attributeId: v.attribute_id,
      optionId: v.option_id,
      visible: v.visible,
      position: v.position,
    })),
    categoryIds: d.category_ids,
    primaryCategoryId: d.primary_category_id,
    tagIds: d.tag_ids,
    kind: d.kind,
    typeId: d.product_type_id,
    revision: d.revision,
    schemaVersion: d.schema_version,
    content: d.content,
    locales: d.locales,
    title: d.title,
    axes: d.axes.map((a) => ({
      attributeId: a.attribute_id,
      optionIds: a.option_ids,
      position: a.position,
    })),
    defaultSelection: d.default_selection,
    variants: d.variants.map((v) => ({
      id: v.id,
      selection: v.selection,
      virtual: v.virtual,
      downloadable: v.downloadable,
      content: v.content,
      locales: v.locales,
      effectiveTitle: v.effective_title,
      titleSource: v.title_source,
    })),
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
export function productItem(d: ProductListItemDTO): CollectionItem {
  return {
    id: d.id,
    label: d.title ?? `Товар ${d.id}`,
    description: `${d.kind.toUpperCase()} · Позиций: ${d.variant_count}`,
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
export function variantFromDto(d: GetVariantResponse): ProductVariant {
  return {
    id: d.id,
    selection: d.selection,
    virtual: d.virtual,
    downloadable: d.downloadable,
    content: d.content,
    locales: d.locales,
    effectiveTitle: d.effective_title,
    titleSource: d.title_source,
  };
}
export function structureToDto(
  d: ProductStructureDraft,
): SimpleStructureDTO | VariableStructureDTO {
  const variant = (v: {
    id: string | null;
    selection: Record<string, string>;
    virtual: boolean;
  }) => ({ variant_id: v.id, selection: v.selection, virtual: v.virtual });
  if (d.kind === "simple")
    return { kind: "simple", variant: variant(d.variant) };
  return {
    kind: "variable",
    axes: d.axes.map((a) => ({
      attribute_id: a.attributeId,
      option_ids: a.optionIds,
      position: a.position,
    })),
    default_selection: d.defaultSelection,
    variants: d.variants.map(variant),
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
