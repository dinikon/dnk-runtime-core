// Самостоятельные модели форм; транспортные DTO остаются на границе API.
export type ProductSection =
  | "content"
  | "status"
  | "sku"
  | "virtual"
  | "price"
  | "stock"
  | "measurements"
  | "galleries";
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
export type ProductTab = "general" | "inventory" | "shipping";
export interface ProductOverviewModel {
  title: string;
  status: string;
  sku: string | null;
  price: string;
  stock: string;
  available: boolean;
  body: string;
  images: { id: string; url: string; alt: string; caption: string }[];
  primaryImage: string | null;
  measurements: { label: string; value: string }[];
  quantity: number | null;
}

export type ProductStatus = "draft" | "active" | "archived";
export interface ProductPatch {
  status?: ProductStatus;
  sku?: string | null;
  virtual?: boolean;
  price_specification?: ProductPrice | null;
  stock?: ProductStock;
  weight?: ProductWeight | null;
  dimensions?: ProductDimensions | null;
  content?: {
    expected_schema_version: number;
    values: Record<string, string>;
  } | null;
  gallery?: ProductGallery | null;
}
