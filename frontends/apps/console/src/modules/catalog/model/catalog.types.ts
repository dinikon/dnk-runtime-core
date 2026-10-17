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

  parentId: string | null;
  childCount: number;
}
export interface CatalogTag {
  id: string;
  label: string | null;
}
export interface CatalogAttributeOption {
  id: string;
  label: string | null;
  position: number;
  locales: string[];
}
export interface CatalogAttribute {
  id: string;
  label: string | null;

  locales: string[];
  options: CatalogAttributeOption[];
}
export interface AttributeOptionDraft {
  id: string | null;
  label: string | null;
}
export interface CollectionItem {
  id: string;
  label: string;
  description: string;

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
