import type { OfferFilters } from "../api/contracts";

export const priceListKeys = {
  all: ["price-lists"] as const,
  list: () => [...priceListKeys.all, "list"] as const,
  detail: (id: string) => [...priceListKeys.all, "detail", id] as const,
  offers: (filters: OfferFilters) => [...priceListKeys.all, "offers", filters] as const,
  history: (id: string) => [...priceListKeys.all, "history", id] as const,
};

