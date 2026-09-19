import type { OfferFilters, OfferHistoryFilters, PriceListScope } from "../api/contracts";

export const priceListKeys = {
  all: ["price-lists"] as const,
  list: (scope: PriceListScope = "current") => [...priceListKeys.all, "list", scope] as const,
  detail: (id: string) => [...priceListKeys.all, "detail", id] as const,
  offers: (filters: OfferFilters) => [...priceListKeys.all, "offers", filters] as const,
  history: (id: string, filters: OfferHistoryFilters) => [...priceListKeys.all, "history", id, filters] as const,
};
