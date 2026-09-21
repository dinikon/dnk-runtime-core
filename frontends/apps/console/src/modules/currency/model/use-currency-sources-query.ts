import { currencyQueryKeys } from "./query-keys";
import { currencyApi } from "../api/currency.api";
import { useQuery } from "@tanstack/vue-query";

export function useCurrencySources() {
  return useQuery({
    queryKey: currencyQueryKeys.sources,
    queryFn: currencyApi.sources,
  });
}
