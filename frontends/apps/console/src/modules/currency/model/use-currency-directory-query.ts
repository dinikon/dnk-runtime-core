import { currencyQueryKeys } from "./query-keys";
import { currencyApi } from "../api/currency.api";
import { useQuery } from "@tanstack/vue-query";

export function useCurrencyDirectory() {
  return useQuery({
    queryKey: currencyQueryKeys.directory,
    queryFn: currencyApi.directory,
  });
}
