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
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}

export interface CatalogListItem {
  id: string;
  status: import("./product.types").ProductStatus;
  sku: string | null;
  title: string | null;
  price: string | null;
  currency: string | null;
  availableForSale: boolean;
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
