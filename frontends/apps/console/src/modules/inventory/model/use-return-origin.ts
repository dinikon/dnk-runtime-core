import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { ReturnOrigin } from "./return-origin.types";
import { returnKeys } from "./return.query-keys";
import { getReturnOrigin } from "../api/return-origin.api";
export function useReturnOrigin(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReturnOrigin, Error> {
  return useQuery({
    queryKey: computed(() => returnKeys.origin(scope.key.value, id.value)),
    queryFn: ({ queryKey, signal }) => getReturnOrigin(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    retry: false,
    staleTime: 0,
  });
}
