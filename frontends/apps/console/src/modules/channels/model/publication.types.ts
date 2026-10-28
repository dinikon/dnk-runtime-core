export interface PublicationItem {
  id: string;
  externalId: string;
  kind: string;
  title: string | null;
  sku: string | null;
  url: string | null;
  mainImageUrl: string | null;
  price: string | null;
  regularPrice: string | null;
  salePrice: string | null;
  currency: string;
  quantity: string | null;
  stockMode: string;
  stockSourcePublicationId: string;
  availability: string | null;
  status: string | null;
  lastSeenAt: string;
  staleConfiguration: boolean;
}
export interface PublicationCard {
  id: string;
  rootKind: string;
  rootExternalId: string;
  rootSku: string | null;
  rootMainImageUrl: string | null;
  title: string | null;
  selectedPublicationId: string | null;
  items: PublicationItem[];
  minPrice: string | null;
  maxPrice: string | null;
  currency: string | null;
  lastSeenAt: string;
}
export interface PublicationPage {
  items: PublicationCard[];
  total: number;
  offset: number;
  limit: number;
  locale: string;
  locales: string[];
}
export interface PublicationDetails {
  card: PublicationCard;
  locale: string;
  locales: string[];
}
export interface PublicationFilters {
  search: string;
  offset: number;
  limit: number;
  locale: string;
}
export interface PublicationSyncRun {
  id: string;
  configRevision: number;
  revision: number;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  processedCount: number;
  skippedCount: number;
  pagesCount: number;
  automatic: boolean;
  errorCode: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  recoveryRequired: boolean;
}
export interface StartedPublicationSync {
  id: string;
  status: string;
}
