import { currencyQueryKeys } from "./query-keys";
import { currencyApi } from "../api/currency.api";
import { useQuery } from "@tanstack/vue-query";
import { computed, type Ref } from "vue";

export function useCurrencyRates(provider: Ref<string>, offset: Ref<number>) {
  return useQuery({
    queryKey: computed(() =>
      currencyQueryKeys.rates(provider.value, offset.value),
    ),
    queryFn: () => currencyApi.rates(provider.value, offset.value),
  });
}
