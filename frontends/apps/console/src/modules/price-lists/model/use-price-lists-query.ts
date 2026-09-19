import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { priceListsApi } from "../api/price-lists.api";
import { priceListKeys } from "./query-keys";

import type { PriceListScope } from "./types";

export function usePriceListsQuery(scope?: Ref<PriceListScope>) {
  return useQuery({
    queryKey: computed(() => priceListKeys.list(scope?.value ?? "current")),
    queryFn: ({ signal }) => priceListsApi.list(scope?.value ?? "current", signal),
  });
}
