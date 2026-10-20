export interface DraftValues {
  titles: Record<string, string>;
  descriptions?: Record<string, string>;
  gallery?: string[];
  primaryImageId?: string | null;
  sku: string | null;
  regularPrice: string | null;
  salePrice: string | null;
  currency: string | null;
  manageStock: boolean;
  quantity: string | null;
  stockStatus: string | null;
  backorders: string;
}
export interface DraftIssue {
  field: string;
  message: string;
}
export interface DraftPreview {
  publicationId: string;
  locale: string;
  observedRevision: number;
  values: DraftValues;
  issues: DraftIssue[];
  warnings: string[];
  mainImageUrl: string | null;
  origins: Record<string, string>;
}
export interface CatalogCandidate {
  id: string;
  title: string | null;
  sku: string | null;
  status: string;
  canBind: boolean;
  reasonCode: string | null;
  representationRevision: number | null;
}
export interface CatalogCandidatesPage {
  publicationId: string;
  locale: string;
  items: CatalogCandidate[];
  total: number;
}
export interface CatalogCandidatesInput {
  publicationId: string;
  locale: string;
  search: string;
  offset: number;
  limit: number;
}
export interface DraftPreviewInput {
  publicationId: string;
  observedRevision: number;
  locale: string;
}
export interface BindPublicationInput {
  publicationId: string;
  catalogItemId: string;
  expectedRevision: number | null;
}
export interface BoundPublication {
  catalogItemId: string;
  representationId: string;
  bindingId: string;
  revision: number;
}
export interface UnbindPublicationInput {
  publicationId: string;
  bindingId: string;
  expectedRevision: number;
}
export interface CreateDraftInput {
  preparationId?: string;
  preparationRevision?: number;
  publicationId: string;
  requestKey: string;
  observedRevision: number;
  values: DraftValues;
}
export interface CreatedCatalogDraft {
  catalogItemId: string;
  representationId: string;
  bindingId: string;
}
export interface PublicationSnapshot {
  id: string;
  observedRevision: number;
  titleLocale: string | null;
}
