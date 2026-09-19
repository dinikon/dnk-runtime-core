export type PriceListStatus = "draft" | "ready" | "active" | "paused" | "invalid";
export type SourceFormat = "xml" | "yaml" | "xlsx";

export interface MappingField {
  selector?: string;
  selectors?: string[];
  constant?: unknown;
  default?: unknown;
  type?: "decimal" | "integer";
  required?: boolean;
  trim?: boolean;
  lower?: boolean;
  replace?: Record<string, string>;
  map?: Record<string, unknown>;
}

export type MappingConfig = Record<string, MappingField>;

export interface PriceList {
  id: string;
  title: string;
  status: PriceListStatus;
  source_format: SourceFormat;
  source_preset: "prom_xml" | null;
  source_url_display: string;
  source_config: Record<string, unknown>;
  mapping_config: MappingConfig;
  cron_expression: string | null;
  timezone: string;
  next_sync_at: string | null;
  last_success_at: string | null;
  last_error_at: string | null;
  schedule_revision: number;
  active_offer_count?: number;
  last_run_status?: string | null;
}

export interface PreviewResult {
  format: SourceFormat;
  content_type: string;
  size: number;
  checksum: string;
  sheets?: string[];
  columns?: string[];
  paths?: string[];
  rows: Array<{
    row_number: number;
    values: Record<string, unknown>;
    errors: string[];
  }>;
}

export interface PartnerOffer {
  id: string;
  sku: string;
  external_id: string;
  title: string;
  lifecycle_status: string;
  price_list_id: string;
  price_list_title: string;
  purchase_price: string | null;
  rrp: string | null;
  currency: string | null;
  recommended_retail_income: string | null;
  margin_percent: string | null;
  availability: "in_stock" | "out_of_stock" | "unknown" | null;
  quantity: number | null;
  observed_at: string | null;
}

export interface PartnerOfferState {
  id: string;
  observed_at: string;
  purchase_price: string;
  rrp: string | null;
  currency: string;
  availability: string;
  quantity: number | null;
  change_reason: string;
  recommended_retail_income: string | null;
  margin_percent: string | null;
}

export interface OffersResponse {
  items: PartnerOffer[];
  total: number;
  offset: number;
  limit: number;
}

export interface SyncRun {
  id: string;
  status: string;
  trigger: string;
  started_at: string;
  finished_at: string | null;
  counters: Record<string, number>;
  error_summary: string | null;
}

export interface OfferFilters {
  q: string;
  priceListId: string;
  purchasePriceMin: string;
  purchasePriceMax: string;
  incomeMin: string;
  incomeMax: string;
  marginMin: string;
  marginMax: string;
  availability: string;
  hasRrp: string;
  sort: string;
  direction: "asc" | "desc";
  page: number;
  limit: number;
}
