import type { LocationQuery } from "vue-router";
import type { OfferFilters, OfferHistoryFilters } from "../api/contracts";

export const defaultOfferFilters: OfferFilters = {
  businessDate: "",
  q: "",
  priceListId: "",
  purchasePriceMin: "",
  purchasePriceMax: "",
  incomeMin: "",
  incomeMax: "",
  marginMin: "",
  marginMax: "",
  availability: "",
  hasRrp: "",
  sort: "observed_at",
  direction: "desc",
  page: 1,
  limit: 50,
  includeArchived: false,
};

export const defaultOfferHistoryFilters: OfferHistoryFilters = {
  observedFrom: "",
  observedTo: "",
  purchasePriceMin: "",
  purchasePriceMax: "",
  rrpMin: "",
  rrpMax: "",
  incomeMin: "",
  incomeMax: "",
  marginMin: "",
  marginMax: "",
  quantityMin: "",
  quantityMax: "",
  availability: "",
  changeReason: "",
  sort: "observed_at",
  direction: "desc",
  page: 1,
  limit: 50,
};

function first(value: LocationQuery[string]): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

export function filtersFromQuery(query: LocationQuery): OfferFilters {
  const direction = first(query.direction);
  return {
    businessDate: first(query.business_date),
    q: first(query.q),
    priceListId: first(query.price_list_id),
    purchasePriceMin: first(query.purchase_price_min),
    purchasePriceMax: first(query.purchase_price_max),
    incomeMin: first(query.income_min),
    incomeMax: first(query.income_max),
    marginMin: first(query.margin_min),
    marginMax: first(query.margin_max),
    availability: first(query.availability),
    hasRrp: first(query.has_rrp),
    sort: first(query.sort) || defaultOfferFilters.sort,
    direction: direction === "asc" ? "asc" : "desc",
    page: Math.max(1, Number(first(query.page)) || 1),
    limit: [25, 50, 100].includes(Number(first(query.limit)))
      ? Number(first(query.limit))
      : defaultOfferFilters.limit,
    includeArchived: first(query.include_archived) === "true",
  };
}

export function filtersToQuery(filters: OfferFilters): Record<string, string> {
  const entries: Array<[string, string | number]> = [
    ["business_date", filters.businessDate],
    ["q", filters.q],
    ["price_list_id", filters.priceListId],
    ["purchase_price_min", filters.purchasePriceMin],
    ["purchase_price_max", filters.purchasePriceMax],
    ["income_min", filters.incomeMin],
    ["income_max", filters.incomeMax],
    ["margin_min", filters.marginMin],
    ["margin_max", filters.marginMax],
    ["availability", filters.availability],
    ["has_rrp", filters.hasRrp],
    ["sort", filters.sort],
    ["direction", filters.direction],
    ["page", filters.page],
    ["limit", filters.limit],
    ["include_archived", filters.includeArchived ? "true" : ""],
  ];
  return Object.fromEntries(
    entries
      .filter(([, value]) => value !== "" && value !== 0)
      .map(([key, value]) => [key, String(value)]),
  );
}

export function formatMoney(value: string | null, currency = "UAH"): string {
  if (value === null) return "—";
  return new Intl.NumberFormat("uk-UA", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(value));
}
