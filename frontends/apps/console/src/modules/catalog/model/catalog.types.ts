export interface SchemaBlock {
  blockId: string;
  code: string;
  label: string | null;
  valueType: "text" | "rich_text";
  scope: "PRODUCT" | "VARIANT";
  required: boolean;
  position: number;
}
export interface BlockLink {
  blockId: string;
  scope: "PRODUCT" | "VARIANT";
  required: boolean;
  position: number;
}
export type ProductKind = "simple" | "variable";
export interface ProductAxis {
  attributeId: string;
  optionIds: string[];
  position: number;
}
export interface ProductVariant {
  id: string;
  selection: Record<string, string>;
  virtual: boolean;
  downloadable: boolean;
  content: Record<string, string> | null;
  locales: string[];
  effectiveTitle: string | null;
  titleSource: "PRODUCT" | "VARIANT" | null;
}
export interface ProductAttributeValue {
  attributeId: string;
  optionId: string;
  visible: boolean;
  position: number;
}
export interface CatalogCategory {
  id: string;
  label: string | null;
  revision: number;
  parentId: string | null;
  childCount: number;
}
export interface CatalogTag {
  id: string;
  label: string | null;
  revision: number;
}
export interface Product {
  attributeValues: ProductAttributeValue[];
  categoryIds: string[];
  primaryCategoryId: string | null;
  tagIds: string[];
  id: string;
  kind: ProductKind;
  typeId: string;
  revision: number;
  schemaVersion: number;
  content: Record<string, string> | null;
  locales: string[];
  title: string | null;
  axes: ProductAxis[];
  defaultSelection: Record<string, string> | null;
  variants: ProductVariant[];
}
export interface CatalogAttributeOption {
  id: string;
  code: string;
  label: string | null;
  position: number;
  locales: string[];
}
export interface CatalogAttribute {
  id: string;
  code: string;
  label: string | null;
  revision: number;
  locales: string[];
  options: CatalogAttributeOption[];
}
export interface VariantStructureDraft {
  id: string | null;
  selection: Record<string, string>;
  virtual: boolean;
}
export interface VariableStructureDraft {
  kind: "variable";
  axes: ProductAxis[];
  defaultSelection: Record<string, string> | null;
  variants: VariantStructureDraft[];
}
export interface SimpleStructureDraft {
  kind: "simple";
  variant: VariantStructureDraft;
}
export type ProductStructureDraft =
  SimpleStructureDraft | VariableStructureDraft;
export interface AttributeOptionDraft {
  id: string | null;
  code: string;
  label: string;
}
export interface ProductType {
  id: string;
  code: string;
  label: string | null;
  system: boolean;
  revision: number;
  schemaVersion: number;
  blocks: SchemaBlock[];
  locales: string[];
}
export interface ContentBlock {
  id: string;
  code: string;
  label: string | null;
  system: boolean;
  revision: number;
  valueType: "text" | "rich_text";
  locales: string[];
}
export interface CollectionItem {
  id: string;
  label: string;
  description: string;
  revision: number;
  system: boolean;
}
export type CollectionKind =
  "products" | "product-types" | "content-blocks" | "attributes" | "tags";
export interface DefinitionInput {
  code: string;
  label: string;
  valueType: "text" | "rich_text";
}
export interface LocaleOption {
  code: string;
  name: string;
  active: boolean;
}
