import type { OfferConversion } from "@/modules/currency/model/types";
export type PriceListStatus =
  "draft" | "ready" | "active" | "paused" | "invalid" | "archived";
export type SourceFormat = "xml" | "yaml" | "xlsx";
export type PriceListScope = "current" | "archived" | "all";

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
  mapping_version: number;
  cron_expression: string | null;
  timezone: string;
  new_item_policy: "create" | "quarantine" | "ignore";
  missing_item_policy:
    "mark_out_of_stock" | "mark_missing" | "keep_last" | "archive";
  missing_threshold: number;
  next_sync_at: string | null;
  last_success_at: string | null;
  last_error_at: string | null;
  archived_at: string | null;
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
  historical_conversion?: OfferConversion | null;
  current_conversion?: OfferConversion | null;
  display_conversion?: OfferConversion | null;
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
  change_count: number;
}

export interface PartnerOfferState {
  historical_conversion?: OfferConversion | null;
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

export interface OfferHistoryResponse {
  items: PartnerOfferState[];
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
  businessDate: string;
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
  includeArchived: boolean;
}

export interface OfferHistoryFilters {
  observedFrom: string;
  observedTo: string;
  purchasePriceMin: string;
  purchasePriceMax: string;
  rrpMin: string;
  rrpMax: string;
  incomeMin: string;
  incomeMax: string;
  marginMin: string;
  marginMax: string;
  quantityMin: string;
  quantityMax: string;
  availability: string;
  changeReason: string;
  sort: string;
  direction: "asc" | "desc";
  page: number;
  limit: number;
}
