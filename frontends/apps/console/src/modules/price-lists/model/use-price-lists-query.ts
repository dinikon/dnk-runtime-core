import { useQuery } from "@tanstack/vue-query";
import { priceListsApi } from "../api/price-lists.api";
import { priceListKeys } from "./query-keys";

export function usePriceListsQuery() {
  return useQuery({
    queryKey: priceListKeys.list(),
    queryFn: ({ signal }) => priceListsApi.list(signal),
  });
}
