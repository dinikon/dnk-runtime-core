import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InternalMoveExecutionResult } from "./internal-move-execution-result.types";
import { getInternalMoveExecutionResult } from "../api/internal-move-execution-result.api";
export function useInternalMoveExecutionResult(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<InternalMoveExecutionResult, Error> {
  return useQuery({
    queryKey: computed(
      () =>
        [
          "inventory",
          ...scope.key.value,
          "internal-move-execution-result",
          id.value,
        ] as const,
    ),
    queryFn: ({ queryKey, signal }) =>
      getInternalMoveExecutionResult(queryKey[5], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 60000,
    retry: false,
  });
}
