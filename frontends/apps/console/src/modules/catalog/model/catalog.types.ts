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
export interface Product {
  id: string;
  kind: string;
  typeId: string;
  revision: number;
  schemaVersion: number;
  content: Record<string, string> | null;
  locales: string[];
  variantId: string;
  virtual: boolean;
  downloadable: boolean;
  variantContent: Record<string, string> | null;
  variantLocales: string[];
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
export type CollectionKind = "products" | "product-types" | "content-blocks";
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
