import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { priceListsApi } from "../api/price-lists.api";
import { priceListKeys } from "./query-keys";

export function usePriceListQuery(id: Ref<string>) {
  return useQuery({
    queryKey: computed(() => priceListKeys.detail(id.value)),
    queryFn: ({ signal }) => priceListsApi.get(id.value, signal),
    refetchInterval: (query) =>
      query.state.data?.status === "active" && !query.state.data.last_success_at ? 5000 : false,
  });
}
