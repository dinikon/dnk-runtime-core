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
export interface AttributeOptionDraft {
  id: string | null;
  code: string;
  label: string;
}
export interface CollectionItem {
  id: string;
  label: string;
  description: string;
  revision: number;
  system: boolean;
}
export interface LocaleOption {
  code: string;
  name: string;
  active: boolean;
}
export type CollectionKind = "attributes" | "tags";
export interface CatalogItem {
  id: string;
  rootId: string;
  rootRevision: number;
  kind: import("../api/catalog.dto").ItemKind;
  title: string | null;
  own: import("../api/catalog.dto").OwnItemDTO;
  effective: import("../api/catalog.dto").ReadItemDTO["effective"];
  stockStatus: string | null;
  priceMin: string | null;
  priceMax: string | null;
  priceIncomplete: boolean;
}
