export interface CreatePublicationCatalogResult {
  catalogItemId: string;
  bindingGroupId: string;
  created: boolean;
  warnings: string[];
}
export interface PublicationCreationState {
  pending: boolean;
  error: string;
  catalogItemId: string | null;
  warnings: string[];
}
