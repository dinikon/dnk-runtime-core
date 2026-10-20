import type { DraftValues } from "./catalog-links.types";
export interface ImportDraftValues extends DraftValues {
  copyPrices?: boolean;
  descriptions: Record<string, string>;
  gallery: string[];
  primaryImageId: string | null;
}
export interface PublicationImportImage {
  id: string;
  previewUrl: string | null;
  alt: string;
  errorCode: string | null;
}
export interface PublicationImport {
  id: string;
  publicationId: string;
  status: string;
  revision: number;
  observedRevision: number;
  expiresAt: string;
  readAt: string | null;
  errorCode: string | null;
  values: ImportDraftValues | null;
  translations: Record<string, { title: string | null; body: string | null }>;
  images: PublicationImportImage[];
  warnings: string[];
}
export interface StartPublicationImportInput {
  publicationId: string;
  preparationId: string;
  observedRevision: number;
}
export interface ChangePublicationImportInput {
  preparationId: string;
  revision: number;
}
export interface ChangedPublicationImport {
  preparationId: string;
  revision: number;
}
