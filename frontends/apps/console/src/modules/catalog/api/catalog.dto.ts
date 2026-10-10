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
export interface ProductAxisDTO {
  attribute_id: string;
  option_ids: string[];
  position: number;
}
export interface ProductVariantDTO {
  id: string;
  selection: Record<string, string>;
  virtual: boolean;
  downloadable: boolean;
  content: Record<string, string> | null;
  locales: string[];
  effective_title: string | null;
  title_source: "PRODUCT" | "VARIANT" | null;
}
export interface ProductAttributeValueDTO {
  attribute_id: string;
  option_id: string;
  visible: boolean;
  position: number;
}
export interface GetProductResponse {
  attribute_values: ProductAttributeValueDTO[];
  category_ids: string[];
  primary_category_id: string | null;
  tag_ids: string[];
  id: string;
  kind: "simple" | "variable";
  product_type_id: string;
  revision: number;
  schema_version: number;
  content: Record<string, string> | null;
  locales: string[];
  title: string | null;
  axes: ProductAxisDTO[];
  default_selection: Record<string, string> | null;
  variants: ProductVariantDTO[];
}
export interface ProductListItemDTO {
  id: string;
  kind: "simple" | "variable";
  product_type_id: string;
  revision: number;
  schema_version: number;
  content: Record<string, string> | null;
  locales: string[];
  title: string | null;
  variant_count: number;
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
  kind: "simple" | "variable";
  revision: number;
  schema_version: number;
  selection: Record<string, string>;
  content: Record<string, string> | null;
  locales: string[];
  virtual: boolean;
  downloadable: boolean;
  effective_title: string | null;
  title_source: "PRODUCT" | "VARIANT" | null;
}
export interface VariantStructureDTO {
  variant_id: string | null;
  selection: Record<string, string>;
  virtual: boolean;
}
export interface VariableStructureDTO {
  kind: "variable";
  axes: ProductAxisDTO[];
  default_selection: Record<string, string> | null;
  variants: VariantStructureDTO[];
}
export interface SimpleStructureDTO {
  kind: "simple";
  variant: VariantStructureDTO;
}
export interface CreateVariableProductRequest {
  product_type_id: string | null;
  structure: VariableStructureDTO;
}
export interface CreateVariableProductResponse {
  id: string;
  revision: number;
}
export interface ReplaceVariantsRequest {
  expected_revision: number;
  structure: VariableStructureDTO;
}
export interface ReplaceVariantsResponse {
  id: string;
  revision: number;
}
export interface ChangeProductKindRequest {
  expected_revision: number;
  structure: SimpleStructureDTO | VariableStructureDTO;
}
export interface ChangeProductKindResponse {
  id: string;
  revision: number;
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
export interface SetProductAttributesRequest {
  expected_revision: number;
  values: ProductAttributeValueDTO[];
}
export interface SetProductAttributesResponse {
  id: string;
  revision: number;
}
export interface SetProductCategoriesRequest {
  expected_revision: number;
  category_ids: string[];
  primary_category_id: string | null;
}
export interface SetProductCategoriesResponse {
  id: string;
  revision: number;
}
export interface SetProductTagsRequest {
  expected_revision: number;
  tag_ids: string[];
}
export interface SetProductTagsResponse {
  id: string;
  revision: number;
}
