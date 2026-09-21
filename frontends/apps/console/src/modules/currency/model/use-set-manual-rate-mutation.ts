import { useMutation } from "@tanstack/vue-query";
import { currencyApi } from "../api/currency.api";

export function useSetManualRateMutation() {
  return useMutation({ mutationFn: currencyApi.manual });
}
