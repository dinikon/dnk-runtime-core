import type {
  ProductPrice,
  ProductWeight,
  ProductDimensions,
  ProductStock,
  ProductGallery,
} from "./product.types";
export interface LocaleOption {
  code: string;
  name: string;
  active: boolean;
}
export interface CatalogItemSources {
  title: string | null;
  body: string | null;
  gallery: string | null;
  weight: string | null;
  dimensions: string | null;
  stock: string;
}
export interface CatalogItem {
  id: string;
  title: string | null;

  kind?: "simple" | "variable" | "variant";
  parent_id?: string | null;
  stock_source?: "own" | "parent";
  variant_count?: number;
  min_price?: string | null;
  max_price?: string | null;
  currency?: string | null;
  mixed_currencies?: boolean;
  effective_content?: Record<string, string> | null;
  effective_gallery?: ProductGallery | null;
  effective_stock?: ProductStock | null;
  effective_weight?: ProductWeight | null;
  effective_dimensions?: ProductDimensions | null;
  sources?: CatalogItemSources | null;
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
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}

export interface CatalogListItem {
  manageStock?: boolean;
  stockQuantity?: number | null;
  stockSource?: "own" | "parent";
  kind?: "simple" | "variable" | "variant";
  parent_id?: string | null;
  variant_count?: number;
  min_price?: string | null;
  max_price?: string | null;
  mixed_currencies?: boolean;
  id: string;
  status: import("./product.types").ProductStatus;
  sku: string | null;
  title: string | null;
  price: string | null;
  currency: string | null;
  availableForSale: boolean;
  stockStatus?: ProductStock["stock_status"];
  primaryImage?: ProductGallery["images"][number] | null;
}
export interface CatalogItemsPage {
  items: CatalogListItem[];
  total: number;
  offset: number;
  limit: number;
  as_of: string;
}
export interface CatalogSchema {
  locale: string;
  schema: {
    id: string;
    code: string;
    label: string | null;
    schema_version: number;
    blocks: {
      id: string;
      code: string;
      value_type: string;
      required: boolean;
      position: number;
      label: string | null;
    }[];
  };
}
