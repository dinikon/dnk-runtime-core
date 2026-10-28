export interface PublicationItemDto {
  id: string;
  external_id: string;
  kind: string;
  title: string | null;
  sku: string | null;
  url: string | null;
  main_image_url: string | null;
  price: string | null;
  regular_price: string | null;
  sale_price: string | null;
  currency: string;
  quantity: string | null;
  stock_mode: string;
  stock_source_publication_id: string;
  availability: string | null;
  status: string | null;
  last_seen_at: string;
  stale_configuration: boolean;
}
export interface PublicationBindingDto {
  id: string;
  catalog_root_id: string;
  catalog_title: string | null;
  mode: string;
  state: string;
}
export interface PublicationCardDto {
  bindings: PublicationBindingDto[];
  id: string;
  root_kind: string;
  root_external_id: string;
  root_sku: string | null;
  root_main_image_url: string | null;
  title: string | null;
  selected_publication_id: string | null;
  items: PublicationItemDto[];
  min_price: string | null;
  max_price: string | null;
  currency: string | null;
  last_seen_at: string;
}
export interface ListPublicationsDto {
  items: PublicationCardDto[];
  total: number;
  offset: number;
  limit: number;
  locale: string;
  locales: string[];
}
export interface GetPublicationDto {
  card: PublicationCardDto;
  locale: string;
  locales: string[];
}
export interface SyncRunDto {
  id: string;
  config_revision: number;
  revision: number;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  processed_count: number;
  skipped_count: number;
  pages_count: number;
  automatic: boolean;
  error_code: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  recovery_required: boolean;
}
export interface LatestSyncRunDto {
  sync_run: SyncRunDto | null;
}
export interface StartSyncRunDto {
  id: string;
  status: "queued" | "running";
}
