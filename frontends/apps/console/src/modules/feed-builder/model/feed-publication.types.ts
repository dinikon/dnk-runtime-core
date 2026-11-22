export type PublicationStatus = "DRAFT" | "ENABLED" | "PAUSED" | "ARCHIVED";
export interface PublicationReference {
  itemId: string;
  variantId: string | null;
}
export interface PublicationChoice extends PublicationReference {
  title: string;
  sku: string | null;
  kind: "simple" | "variant";
}
export interface Publication extends PublicationReference {
  id: string;
  feedId: string;
  status: PublicationStatus;
  version: number;
  title: string | null;
  parentTitle: string | null;
  sku: string | null;
  kind: string | null;
  sourceAvailable: boolean;
  overridesCount: number;
  createdAt: string;
  updatedAt: string;
}
export interface PublicationFilters {
  search: string;
  status: PublicationStatus | "";
  locale: string;
  offset: number;
  limit: number;
}
export interface PublicationPage {
  feedId: string;
  feedVersion: number;
  feedStatus: string;
  items: Publication[];
  total: number;
  counts: Partial<Record<PublicationStatus, number>>;
}
export interface AddPublications {
  feedId: string;
  expectedFeedVersion: number;
  references: PublicationReference[];
}
export interface AddedPublications {
  feedId: string;
  feedVersion: number;
  items: (PublicationReference & {
    id: string;
    status: PublicationStatus;
    version: number;
    outcome: "CREATED" | "EXISTING";
  })[];
}
export interface ChangePublication {
  id: string;
  expectedVersion: number;
  status: "ENABLED" | "PAUSED";
}
export interface PublicationVersionAction {
  id: string;
  expectedVersion: number;
}
export interface ChangedPublication {
  id: string;
  version: number;
  status: PublicationStatus;
  updatedAt: string;
}
export interface PublicationCatalogChoice {
  id: string;
  title: string;
  sku: string | null;
  kind: "simple" | "variable" | "variant";
  available: boolean;
}
export interface PublicationCatalogPage {
  items: PublicationCatalogChoice[];
  total: number;
}
