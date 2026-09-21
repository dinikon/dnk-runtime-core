import { useMutation } from "@tanstack/vue-query";
import { currencyApi } from "../api/currency.api";

export function useInitializeCurrencyMutation() {
  return useMutation({ mutationFn: currencyApi.initialize });
}
