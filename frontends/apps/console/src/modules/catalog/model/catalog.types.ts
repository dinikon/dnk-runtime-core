import type {
  ProductPrice,
  ProductWeight,
  ProductDimensions,
  ProductStock,
  ProductGallery,
  ProductAttribute,
  ProductMetadata,
} from "./product.types";
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
  title: string | null;
  revision: number;
  product_type_id: string;
  status: "draft" | "active" | "archived";
  sku: string | null;
  virtual: boolean;
  price_specification: ProductPrice | null;
  price: string | null;
  weight: ProductWeight | null;
  dimensions: ProductDimensions | null;
  stock: ProductStock;
  stock_status: "in_stock" | "out_of_stock" | "on_backorder";
  backorders_allowed: boolean;
  backordered: boolean;
  available_for_sale: boolean;
  available_for_publication: boolean;
  content: Record<string, string> | null;
  gallery: ProductGallery | null;
  attributes: ProductAttribute[];
  metadata: ProductMetadata[];
  category_ids: string[];
  primary_category_id: string | null;
  tag_ids: string[];
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}
