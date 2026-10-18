export interface LocaleDTO {
  code: string;
  name: string;
}
export type ItemStatus = "draft" | "active" | "archived";
export interface PriceDTO {
  regular_price: string;
  currency: string;
  sale_price: string | null;
  date_on_sale_from: string | null;
  date_on_sale_to: string | null;
}
export type WeightUnit = "g" | "kg";
export type LengthUnit = "cm" | "m";
export interface MeasurementDTO<U extends WeightUnit | LengthUnit> {
  value: string;
  unit: U;
}
export type WeightDTO = MeasurementDTO<WeightUnit>;
export type LengthDTO = MeasurementDTO<LengthUnit>;
export interface DimensionsDTO {
  length: LengthDTO | null;
  width: LengthDTO | null;
  height: LengthDTO | null;
}
export interface StockDTO {
  manage_stock: boolean;
  stock_quantity: number | null;
  stock_status: "in_stock" | "out_of_stock" | "on_backorder" | null;
  backorders: "no" | "notify" | "yes";
}
export interface ImageDTO {
  id: string;
  file_id: string;
  position: number;
  alt: string;
  caption: string;
}
export interface GalleryDTO {
  images: ImageDTO[];
  primary_image_id: string | null;
}
export interface ReadItemDTO {
  id: string;

  product_type_id: string;
  status: ItemStatus;
  sku: string | null;
  virtual: boolean;
  price_specification: PriceDTO | null;
  price: string | null;
  weight: WeightDTO | null;
  dimensions: DimensionsDTO | null;
  stock: StockDTO;
  stock_status: "in_stock" | "out_of_stock" | "on_backorder";
  backorders_allowed: boolean;
  backordered: boolean;
  available_for_sale: boolean;
  available_for_publication: boolean;
  content: Record<string, string> | null;
  gallery: GalleryDTO | null;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}
export interface GetItemResponse {
  item: ReadItemDTO;
  as_of: string;
}
export interface ListItemsResponse {
  items: ListItemDTO[];
  total: number;
  offset: number;
  limit: number;
  as_of: string;
}
export interface CreateItemResponse {
  id: string;
}
export interface UpdateItemResponse {
  id: string;
}
export interface UploadImageResponse {
  id: string;

  image_id: string;
  file_id: string;
}
export interface DefaultSchemaResponse {
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

export interface ListItemDTO {
  id: string;

  status: ItemStatus;
  sku: string | null;
  title: string | null;
  price: string | null;
  currency: string | null;
  stock_status: string | null;
  primary_image: ImageDTO | null;
  weight: WeightDTO | null;
  dimensions: DimensionsDTO | null;
  available_for_sale: boolean;
}

export interface UpdateItemRequest {
  status?: ItemStatus;
  sku?: string | null;
  virtual?: boolean;
  price_specification?: PriceDTO | null;
  stock?: StockDTO;
  weight?: WeightDTO | null;
  dimensions?: DimensionsDTO | null;
  content?: {
    expected_schema_version: number;
    values: Record<string, string>;
  } | null;
  gallery?: GalleryDTO | null;
}
