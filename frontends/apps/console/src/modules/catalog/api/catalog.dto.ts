export interface LocaleDTO {
  code: string;
  name: string;
}
export interface CreateAttributeRequest {
  code: string;
  locale: string;
  label: string;
}
export interface CreateAttributeResponse {
  id: string;
  revision: number;
}
export interface PutAttributeTranslationRequest {
  expected_revision: number;
  label: string;
}
export interface PutAttributeTranslationResponse {
  id: string;
  revision: number;
}
export interface ReplaceAttributeOptionsRequest {
  expected_revision: number;
  options: { option_id: string | null; code: string; label: string }[];
}
export interface ReplaceAttributeOptionsResponse {
  id: string;
  revision: number;
}
export interface GetAttributeResponse {
  id: string;
  code: string;
  value_type: "enum";
  label: string | null;
  revision: number;
  locales: string[];
  options: {
    id: string;
    code: string;
    label: string | null;
    position: number;
    locales: string[];
  }[];
}
export interface ListAttributeItemDTO {
  id: string;
  code: string;
  label: string | null;
  revision: number;
  option_count: number;
}
export interface ListAttributesResponse {
  items: ListAttributeItemDTO[];
  total: number;
  page: number;
  page_size: number;
}
export interface GetCategoryResponse {
  id: string;
  label: string | null;
  revision: number;
  locales: string[];
  parent_id: string | null;
  child_count: number;
}
export interface ListCategoryItemDTO {
  id: string;
  label: string | null;
  revision: number;
  parent_id: string | null;
  child_count: number;
}
export interface ListCategoriesResponse {
  items: ListCategoryItemDTO[];
  total: number;
  page: number;
  page_size: number;
}
export interface CreateCategoryRequest {
  locale: string;
  label: string;
  parent_id: string | null;
}
export interface CreateCategoryResponse {
  id: string;
  revision: number;
}
export interface PutCategoryContentRequest {
  expected_revision: number;
  label: string;
}
export interface PutCategoryContentResponse {
  id: string;
  revision: number;
}
export interface GetTagResponse {
  id: string;
  label: string | null;
  revision: number;
  locales: string[];
}
export interface ListTagItemDTO {
  id: string;
  label: string | null;
  revision: number;
}
export interface ListTagsResponse {
  items: ListTagItemDTO[];
  total: number;
  page: number;
  page_size: number;
}
export interface CreateTagRequest {
  locale: string;
  label: string;
}
export interface CreateTagResponse {
  id: string;
  revision: number;
}
export interface PutTagTranslationRequest {
  expected_revision: number;
  label: string;
}
export interface PutTagTranslationResponse {
  id: string;
  revision: number;
}
export interface MoveCategoryRequest {
  expected_revision: number;
  parent_id: string | null;
}
export interface MoveCategoryResponse {
  id: string;
  revision: number;
}
export type ItemKind = "simple" | "variable" | "variant";
export type ItemStatus = "draft" | "active" | "archived";
export type ItemSection =
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
export interface OverrideDTO<T> {
  mode: "inherit" | "set" | "clear";
  value: T | null;
}
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
export interface AttributeDTO {
  attribute_id: string;
  option_ids: string[];
  visible: boolean;
  position: number;
  mode: "set" | "clear";
}
export interface MetadataDTO {
  key: string;
  value_type: "text" | "decimal" | "boolean" | null;
  value: string | boolean | null;
  position: number;
  mode: "set" | "clear";
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
export interface AxisDTO {
  attribute_id: string;
  option_ids: string[];
  position: number;
  visible: boolean;
}
export interface SelectionDTO {
  attribute_id: string;
  option_id: string;
}
export interface StructureDTO {
  axes: AxisDTO[];
  variants: { item_id: string | null; selection: SelectionDTO[] }[];
  default_selection: SelectionDTO[] | null;
}
export interface OwnItemDTO {
  id: string;
  kind: ItemKind;
  parent_id: string | null;
  product_type_id: string | null;
  status: ItemStatus;
  sku: string | null;
  virtual: boolean;
  price: PriceDTO | null;
  weight: WeightDTO | null;
  dimensions: DimensionsDTO | null;
  stock: StockDTO;
  translations: Record<string, Record<string, OverrideDTO<string>>>;
  galleries: Record<string, GalleryDTO>;
  attributes: AttributeDTO[];
  metadata: MetadataDTO[];
  selection: { values: [string, string][] };
  axes: AxisDTO[];
  default_selection: { values: [string, string][] } | null;
  category_ids: string[];
  primary_category_id: string | null;
  tag_ids: string[];
  revision: number;
  created_at: string;
  updated_at: string;
}
export interface ReadItemDTO {
  root_id: string;
  root_revision: number;
  own: OwnItemDTO;
  effective: {
    content: Record<string, string> | null;
    virtual: boolean;
    price_specification: PriceDTO | null;
    price: string | null;
    weight: WeightDTO | null;
    dimensions: DimensionsDTO | null;
    stock: StockDTO;
    stock_source_id: string | null;
    gallery: GalleryDTO | null;
    attributes: AttributeDTO[];
    metadata: MetadataDTO[];
    available_for_sale: boolean;
    available_for_publication: boolean;
    origins: Record<
      string,
      { source: string; item_id: string | null; locale: string | null }
    >;
  };
  stock_status: string | null;
  backorders_allowed: boolean | null;
  backordered: boolean | null;
  price_min: string | null;
  price_max: string | null;
  price_incomplete: boolean;
  price_currency: string | null;
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
  root_revision: number;
  child_ids: string[];
}
export interface MutationResponse {
  item_id: string;
  root_id: string;
  item_revision: number;
  root_revision: number;
  child_ids?: string[];
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
  kind: ItemKind;
  root_id: string;
  root_revision: number;
  revision: number;
  status: ItemStatus;
  sku: string | null;
  title: string | null;
  price: string | null;
  currency: string | null;
  price_min: string | null;
  price_max: string | null;
  price_incomplete: boolean;
  stock_status: string | null;
  primary_image: ImageDTO | null;
  weight: WeightDTO | null;
  dimensions: DimensionsDTO | null;
  available_for_sale: boolean;
}
export interface ListVariantsResponse {
  items: ReadItemDTO[];
  total: number;
  offset: number;
  limit: number;
  as_of: string;
}
