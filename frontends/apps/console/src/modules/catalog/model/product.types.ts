import type { CatalogItem } from "./catalog.types";
// Самостоятельные модели форм; транспортные DTO остаются на границе API.
export type ProductSection =
  | "content"
  | "status"
  | "sku"
  | "virtual"
  | "price"
  | "stock"
  | "measurements"
  | "metadata"
  | "attributes"
  | "categories"
  | "tags"
  | "galleries"
  | "structure"
  | "kind";
export type WeightUnit = "g" | "kg";
export type LengthUnit = "cm" | "m";
export interface ProductMeasurement<U extends WeightUnit | LengthUnit> {
  value: string;
  unit: U;
}
export type ProductWeight = ProductMeasurement<WeightUnit>;
export interface ProductDimensions {
  length: ProductMeasurement<LengthUnit> | null;
  width: ProductMeasurement<LengthUnit> | null;
  height: ProductMeasurement<LengthUnit> | null;
}
export interface ProductPrice {
  regular_price: string;
  currency: string;
  sale_price: string | null;
  date_on_sale_from: string | null;
  date_on_sale_to: string | null;
}
export interface ProductStock {
  manage_stock: boolean;
  stock_quantity: number | null;
  stock_status: "in_stock" | "out_of_stock" | "on_backorder" | null;
  backorders: "no" | "notify" | "yes";
}
export interface ProductMetadata {
  key: string;
  value_type: "text" | "decimal" | "boolean" | null;
  value: string | boolean | null;
  position: number;
  mode: "set" | "clear";
}
export interface ProductAttribute {
  attribute_id: string;
  option_ids: string[];
  visible: boolean;
  position: number;
  mode: "set" | "clear";
}
export interface ProductOverride<T> {
  mode: "inherit" | "set" | "clear";
  value: T | null;
}
export interface ProductGallery {
  images: {
    id: string;
    file_id: string;
    position: number;
    alt: string;
    caption: string;
  }[];
  primary_image_id: string | null;
}
export interface ProductSelection {
  attribute_id: string;
  option_id: string;
}
export interface ProductStructure {
  axes: {
    attribute_id: string;
    option_ids: string[];
    position: number;
    visible: boolean;
  }[];
  variants: { item_id: string | null; selection: ProductSelection[] }[];
  default_selection: ProductSelection[] | null;
}
export type ProductTab =
  | "general"
  | "inventory"
  | "shipping"
  | "attributes"
  | "variants"
  | "additional";
export interface ProductEditorDraft {
  dirty: Record<string, boolean>;
  resets: Record<string, number>;
}
export interface VariantRowModel {
  item: CatalogItem;
  label: string;
  image: string | null;
  price: string;
  stock: string;
  status: string;
}
export interface ProductOverviewModel {
  title: string;
  kind: string;
  status: string;
  sku: string | null;
  price: string;
  stock: string;
  available: boolean;
  descriptions: { short: string; full: string };
  images: { id: string; url: string; alt: string; caption: string }[];
  primaryImage: string | null;
  measurements: { label: string; value: string }[];
  attributes: { label: string; value: string }[];
  categories: string[];
  tags: string[];
  sharedQuantity: number | null;
  sharedSource: boolean;
  priceIncomplete: boolean;
}
