import { useMutation } from "@tanstack/vue-query";
import { currencyApi } from "../api/currency.api";

export function useConfigurePolicyMutation() {
  return useMutation({ mutationFn: currencyApi.configure });
}
