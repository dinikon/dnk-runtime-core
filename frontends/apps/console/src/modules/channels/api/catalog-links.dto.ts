import type { PublicationRowDto } from "./channels.dto";
export interface CatalogCandidateDto {
  id: string;
  title: string | null;
  sku: string | null;
  status: string;
  can_bind: boolean;
  reason_code: string | null;
  representation_revision: number | null;
}
export interface ListCatalogCandidatesResponseDto {
  items: CatalogCandidateDto[];
  total: number;
}
export interface PreviewCatalogDraftValuesDto {
  titles: Record<string, string>;
  sku: string | null;
  regular_price: string | null;
  sale_price: string | null;
  currency: string | null;
  manage_stock: boolean;
  quantity: string | null;
  stock_status: string | null;
  backorders: string;
}
export interface PreviewCatalogDraftResponseDto {
  observed_revision: number;
  values: PreviewCatalogDraftValuesDto;
  issues: { field: string; message: string }[];
  warnings: string[];
  main_image_url: string | null;
  origins: Record<string, string>;
}
export interface BindPublicationRequestDto {
  catalog_item_id: string;
  expected_revision: number | null;
}
export interface BindPublicationResponseDto {
  catalog_item_id: string;
  representation_id: string;
  binding_id: string;
  revision: number;
}
export interface UnbindPublicationRequestDto {
  binding_id: string;
  expected_revision: number;
}
export interface CreateCatalogDraftValuesDto {
  descriptions?: Record<string, string>;
  gallery?: string[];
  primary_image_id?: string | null;
  titles: Record<string, string>;
  sku: string | null;
  regular_price: string | null;
  sale_price: string | null;
  currency: string | null;
  manage_stock: boolean;
  quantity: string | null;
  stock_status: string | null;
  backorders: string;
}
export interface CreateCatalogDraftRequestDto {
  preparation_id?: string;
  expected_preparation_revision?: number;
  request_key: string;
  expected_observed_revision: number;
  values: CreateCatalogDraftValuesDto;
}
export interface CreateCatalogDraftResponseDto {
  catalog_item_id: string;
  representation_id: string;
  binding_id: string;
}
export type GetPublicationSnapshotResponseDto = Omit<
  PublicationRowDto,
  | "catalog_item_id"
  | "binding_id"
  | "representation_id"
  | "representation_revision"
>;
