import { computed, type Ref } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { priceListsApi } from "../api/price-lists.api";
import { priceListKeys } from "./query-keys";

export function usePriceListRunsQuery(id: Ref<string>) {
  return useQuery({
    queryKey: computed(() => [...priceListKeys.detail(id.value), "runs"]),
    queryFn: ({ signal }) => priceListsApi.runs(id.value, signal),
    refetchInterval: (query) =>
      query.state.data?.some((run) => ["queued", "downloading", "parsing", "applying"].includes(run.status)) ? 5000 : false,
  });
}
