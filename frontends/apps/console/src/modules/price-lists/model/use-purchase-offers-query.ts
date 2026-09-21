import { useCurrencySettings } from "@/modules/currency/model/queries";
import { computed, type Ref } from "vue";
import { keepPreviousData, useQuery } from "@tanstack/vue-query";
import { priceListsApi } from "../api/price-lists.api";
import { priceListKeys } from "./query-keys";
import type { OfferFilters } from "./types";

export function usePurchaseOffersQuery(
  filters: Ref<OfferFilters>,
  enabled: Ref<boolean>,
) {
  useCurrencySettings();
  return useQuery({
    queryKey: computed(() => priceListKeys.offers(filters.value)),
    queryFn: ({ signal }) => priceListsApi.offers(filters.value, signal),
    placeholderData: keepPreviousData,
    enabled,
  });
}
