export interface BlockLinkDTO {
  block_id: string;
  scope: "PRODUCT" | "VARIANT";
  required: boolean;
  position: number;
}
export interface SchemaBlockDTO extends BlockLinkDTO {
  code: string;
  value_type: "text" | "rich_text";
  label: string | null;
}
export interface LocaleDTO {
  code: string;
  name: string;
}
export interface CreateSimpleProductRequest {
  product_type_id?: string | null;
  virtual?: boolean;
}
export interface CreateSimpleProductResponse {
  id: string;
  revision: number;
  variant_id: string;
}
export interface ChangeProductTypeRequest {
  expected_revision: number;
  product_type_id: string;
}
export interface ChangeProductTypeResponse {
  id: string;
  revision: number;
}
export interface SetVariantPropertiesRequest {
  expected_revision: number;
  virtual: boolean;
  downloadable: boolean;
}
export interface SetVariantPropertiesResponse {
  id: string;
  revision: number;
}
export interface PutProductContentRequest {
  expected_revision: number;
  expected_schema_version: number;
  values: Record<string, string>;
}
export interface PutProductContentResponse {
  id: string;
  revision: number;
}
export interface PutVariantContentRequest {
  expected_revision: number;
  expected_schema_version: number;
  values: Record<string, string>;
}
export interface PutVariantContentResponse {
  id: string;
  revision: number;
}
export interface CreateProductTypeRequest {
  code: string;
  locale: string;
  label: string;
  blocks: BlockLinkDTO[];
}
export interface CreateProductTypeResponse {
  id: string;
  revision: number;
  schema_version: number;
}
export interface PutProductTypeTranslationRequest {
  expected_revision: number;
  label: string;
}
export interface PutProductTypeTranslationResponse {
  id: string;
  revision: number;
}
export interface ReplaceProductTypeSchemaRequest {
  expected_revision: number;
  expected_schema_version: number;
  blocks: BlockLinkDTO[];
}
export interface ReplaceProductTypeSchemaResponse {
  id: string;
  revision: number;
  schema_version: number;
}
export interface CreateContentBlockRequest {
  code: string;
  locale: string;
  label: string;
  value_type: "text" | "rich_text";
}
export interface CreateContentBlockResponse {
  id: string;
  revision: number;
}
export interface UpdateContentBlockRequest {
  expected_revision: number;
  locale: string;
  label: string;
  value_type: "text" | "rich_text";
}
export interface UpdateContentBlockResponse {
  id: string;
  revision: number;
}
export interface GetProductResponse {
  id: string;
  kind: string;
  product_type_id: string;
  revision: number;
  schema_version: number;
  content: Record<string, string> | null;
  locales: string[];
  variant_id: string;
  virtual: boolean;
  downloadable: boolean;
  variant_content: Record<string, string> | null;
  variant_locales: string[];
}
export interface ProductListItemDTO {
  id: string;
  kind: string;
  product_type_id: string;
  revision: number;
  schema_version: number;
  content: Record<string, string> | null;
  locales: string[];
  variant_id: string;
  virtual: boolean;
  downloadable: boolean;
  variant_content: Record<string, string> | null;
  variant_locales: string[];
}
export interface ListProductsResponse {
  items: ProductListItemDTO[];
  total: number;
  page: number;
  page_size: number;
}
export interface GetProductTypeResponse {
  id: string;
  code: string;
  is_system: boolean;
  revision: number;
  label: string | null;
  locales: string[];
  schema_version: number;
  blocks: SchemaBlockDTO[];
}
export interface ProductTypeListItemDTO {
  id: string;
  code: string;
  is_system: boolean;
  revision: number;
  label: string | null;
  locales: string[];
  schema_version: number;
  blocks: SchemaBlockDTO[];
}
export interface ListProductTypesResponse {
  items: ProductTypeListItemDTO[];
  total: number;
  page: number;
  page_size: number;
}
export interface GetContentBlockResponse {
  id: string;
  code: string;
  is_system: boolean;
  revision: number;
  label: string | null;
  locales: string[];
  value_type: "text" | "rich_text";
}
export interface ContentBlockListItemDTO {
  id: string;
  code: string;
  is_system: boolean;
  revision: number;
  label: string | null;
  locales: string[];
  value_type: "text" | "rich_text";
}
export interface ListContentBlocksResponse {
  items: ContentBlockListItemDTO[];
  total: number;
  page: number;
  page_size: number;
}
export interface GetVariantResponse {
  id: string;
  product_id: string;
  revision: number;
  schema_version: number;
  content: Record<string, string> | null;
  locales: string[];
  virtual: boolean;
  downloadable: boolean;
}
