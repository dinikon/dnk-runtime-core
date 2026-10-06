export interface AuditDto {
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}
export interface ProductContentDto {
  locale: string;
  name: string;
  description: string | null;
}
export interface CreateProductDto {
  sku_id: string;
  contents: ProductContentDto[];
}
export type ProductKind = "simple" | "variable";

export interface CreatedProductDto extends AuditDto {
  id: string;
  kind: ProductKind;
  variant_id: string;
  sku_id: string;
  sku_code: string;
  content_locales: string[];
}
export interface ProductDto extends Omit<CreatedProductDto, "variant_id" | "sku_id" | "sku_code"> {
  variant_id: string | null;
  sku_id: string | null;
  sku_code: string | null;
  requested_locale: string;
  content: ProductContentDto | null;
  categories: { id: string; name: string | null }[];
  primary_category_id: string | null;
  variants: ProductVariantDto[];
}
export interface ProductVariantDto {
  id: string;
  sku_id: string;
  sku_code: string;
  content_locales: string[];
  short_description: string | null;
}
export interface ProductListItemDto {
  id: string;
  kind: ProductKind;
  name: string | null;
  variant_count: number;
  primary_category_id: string | null;
  primary_category_name: string | null;
  updated_at: string;
}
export interface VariantStructureDto {
  kind: ProductKind;
  variants: { id?: string; sku_id: string }[];
}
export interface PutContentDto {
  name: string;
  description: string | null;
}
export interface SavedContentDto extends PutContentDto {
  product_id: string;
  locale: string;
  updated_at: string;
  updated_by: string;
}
export interface LocaleDto {
  code: string;
  language_code: string;
  script_code: string | null;
  region_code: string | null;
  country_code: string | null;
  name: string;
}

export interface CategoryListDto {
  id: string;
  parent_id: string | null;
  name: string | null;
}
export interface CategoryTranslationDto {
  locale: string;
  name: string;
}
export interface CategoryDto extends CategoryListDto, AuditDto {
  requested_locale: string;
  translations: CategoryTranslationDto[];
}
export interface CreateCategoryDto {
  parent_id: string | null;
  translations: CategoryTranslationDto[];
}
export interface CreatedCategoryDto extends AuditDto {
  id: string;
  parent_id: string | null;
  locales: string[];
}
export interface SavedCategoryContentDto {
  category_id: string;
  locale: string;
  name: string;
  updated_at: string;
  updated_by: string;
}
export interface MovedCategoryDto {
  id: string;
  parent_id: string | null;
  updated_at: string;
  updated_by: string;
}
export interface ProductCategoriesPayload {
  category_ids: string[];
  primary_category_id: string | null;
}
export interface SavedProductCategoriesDto extends ProductCategoriesPayload {
  product_id: string;
  updated_at: string;
  updated_by: string;
}
