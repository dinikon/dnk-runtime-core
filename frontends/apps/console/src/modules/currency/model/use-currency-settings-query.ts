import { currencyQueryKeys } from "./query-keys";
import { currencyApi } from "../api/currency.api";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { watch, onScopeDispose } from "vue";

export function useCurrencySettings() {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: currencyQueryKeys.settings,
    queryFn: currencyApi.settings,
  });
  let timer: ReturnType<typeof setTimeout> | undefined;
  watch(
    () => query.data.value?.next_business_day_at,
    (next) => {
      if (timer) clearTimeout(timer);
      if (!next) return;
      const delay = Math.max(1000, new Date(next).getTime() - Date.now() + 100);
      timer = setTimeout(
        () => {
          void client.invalidateQueries({
            queryKey: currencyQueryKeys.settings,
          });
          void client.invalidateQueries({
            predicate: (q) => q.queryKey.includes("offers"),
          });
        },
        Math.min(delay, 2147483647),
      );
    },
    { immediate: true },
  );
  onScopeDispose(() => {
    if (timer) clearTimeout(timer);
  });
  return query;
}
