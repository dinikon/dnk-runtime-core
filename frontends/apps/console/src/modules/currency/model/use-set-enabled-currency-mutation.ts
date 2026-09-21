import { useMutation } from "@tanstack/vue-query";
import { currencyApi } from "../api/currency.api";

export function useSetEnabledCurrencyMutation() {
  return useMutation({
    mutationFn: ({ code, enabled }: { code: string; enabled: boolean }) =>
      currencyApi.enable(code, enabled),
  });
}
