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
export interface CreatedProductDto extends AuditDto {
  id: string;
  type: string;
  variant_id: string;
  sku_id: string;
  sku_code: string;
  content_locales: string[];
}
export interface ProductDto extends CreatedProductDto {
  requested_locale: string;
  content: ProductContentDto | null;
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
export interface SkuDto extends AuditDto {
  id: string;
  code: string;
  title: string;
}
export interface LocaleDto {
  code: string;
  language_code: string;
  script_code: string | null;
  region_code: string | null;
  country_code: string | null;
  name: string;
}
