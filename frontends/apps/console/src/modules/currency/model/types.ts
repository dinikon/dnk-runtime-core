export interface CurrencyInfo {
  code: string;
  name: string;
  minor_units: number | null;
  numeric_code: string | null;
  symbol: string | null;
}

export interface CurrencyPolicy {
  default_transaction_currency: string;
  provider_code: "NBU" | "MANUAL";
  rate_date_policy: "exact" | "previous_available";
  rounding_mode:
    "ROUND_HALF_UP" | "ROUND_HALF_EVEN" | "ROUND_DOWN" | "ROUND_UP";
  allow_cross_rate: boolean;
  bridge_currency: string;
  business_timezone: string;
  version: number;
}

export interface CurrencyPeriod {
  id: string;
  currency: string;
  valid_from: string;
  valid_to: string | null;
  reason: string;
}

export interface CurrencySettings {
  configured: boolean;
  policy: CurrencyPolicy | null;
  enabled_currencies: string[];
  functional_currency: string | null;
  future_functional_currency: string | null;
  business_date: string;
  periods: CurrencyPeriod[];
  permissions: string[];
  provider_status: {
    last_available_rate_date: string | null;
    last_import: {
      status: "running" | "succeeded" | "failed";
      started_at: string;
      finished_at: string | null;
      created_count: number;
      updated_count: number;
      error_message: string | null;
    } | null;
  };
}

export interface RateRecord {
  id: string;
  pair: { source: string; target: string };
  rate: string;
  effective_date: string;
  provider_code: string;
  revision: number;
  is_current: boolean;
}

export interface ConvertedMoney {
  original: { amount: string; currency: string };
  converted: { amount: string; currency: string };
  conversion: {
    requested_date: string;
    effective_date: string;
    rate: string;
    provider_code: string;
    derivation: string;
    source_rate_ids: string[];
  };
}

export interface OfferConversion {
  status: "converted" | "unavailable";
  business_date: string | null;
  purchase_price: ConvertedMoney | null;
  rrp: ConvertedMoney | null;
  error_code: string | null;
}

export type PolicyInput = Omit<CurrencyPolicy, "version">;
export type InitializeInput = PolicyInput & {
  enabled_currencies: string[];
  functional_currency: string;
  valid_from: string;
  reason: string;
};
