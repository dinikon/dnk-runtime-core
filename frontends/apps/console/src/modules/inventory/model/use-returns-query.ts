import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { ReturnsPage, ReturnsParams } from "./return.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { returnKeys } from "./return.query-keys";
import { listReturns } from "../api/return.api";
export function useReturnsQuery(
  params: Ref<ReturnsParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReturnsPage, Error> {
  return useQuery({
    queryKey: computed(() => returnKeys.list(scope.key.value, params.value)),
    queryFn: ({ queryKey, signal }) => listReturns(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: false,
  });
}
