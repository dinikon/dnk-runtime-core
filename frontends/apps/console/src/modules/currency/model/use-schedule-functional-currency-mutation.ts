import { useMutation } from "@tanstack/vue-query";
import { currencyApi } from "../api/currency.api";

export function useScheduleFunctionalCurrencyMutation() {
  return useMutation({ mutationFn: currencyApi.schedule });
}
