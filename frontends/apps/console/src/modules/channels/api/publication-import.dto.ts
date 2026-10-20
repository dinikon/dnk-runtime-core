import type { PreviewCatalogDraftValuesDto } from "./catalog-links.dto";
export interface StartPublicationImportRequestDto {
  preparation_id: string;
  expected_observed_revision: number;
}
export interface StartPublicationImportResponseDto {
  preparation_id: string;
}
export interface RetryPublicationImportRequestDto {
  expected_revision: number;
}
export interface RetryPublicationImportResponseDto {
  preparation_id: string;
  revision: number;
}
export interface CancelPublicationImportRequestDto {
  expected_revision: number;
}
export interface CancelPublicationImportResponseDto {
  preparation_id: string;
  revision: number;
}
export interface GetPublicationImportResponseDto {
  preparation_id: string;
  publication_id: string;
  status: string;
  revision: number;
  observed_revision: number;
  created_at: string;
  read_at: string | null;
  expires_at: string;
  error_code: string | null;
  values:
    | (PreviewCatalogDraftValuesDto & {
        descriptions: Record<string, string>;
        gallery: string[];
        primary_image_id: string | null;
      })
    | null;
  translations: Record<string, { title: string | null; body: string | null }>;
  images: {
    id: string;
    preview_url: string | null;
    alt: string;
    error_code: string | null;
  }[];
  warnings: string[];
}
