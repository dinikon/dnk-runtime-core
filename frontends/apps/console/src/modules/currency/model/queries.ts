import { computed, type Ref } from "vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { currencyApi } from "../api/currency.api";

export function useCurrencySettings() {
  return useQuery({
    queryKey: ["currency", "settings"],
    queryFn: currencyApi.settings,
  });
}

export function useCurrencyDirectory() {
  return useQuery({
    queryKey: ["currency", "directory"],
    queryFn: currencyApi.directory,
  });
}

export function useCurrencyRates(provider: Ref<string>, offset: Ref<number>) {
  return useQuery({
    queryKey: computed(() => [
      "currency",
      "rates",
      provider.value,
      offset.value,
    ]),
    queryFn: () => currencyApi.rates(provider.value, offset.value),
  });
}

export function useRefreshCurrency() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: ["currency"] });
}
