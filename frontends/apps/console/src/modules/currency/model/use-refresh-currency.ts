import { currencyQueryKeys } from "./query-keys";
import { useQueryClient } from "@tanstack/vue-query";

export function useRefreshCurrency() {
  const client = useQueryClient();
  return async () => {
    await client.invalidateQueries({ queryKey: currencyQueryKeys.all });
    await client.invalidateQueries({
      predicate: (q) => q.queryKey.includes("offers"),
    });
  };
}
