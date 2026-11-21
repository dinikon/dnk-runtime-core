import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { WriteOffExecutionResult } from "./write-off-execution-result.types";
import { getWriteOffExecutionResult } from "../api/write-off-execution-result.api";
export function useWriteOffExecutionResult(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<WriteOffExecutionResult, Error> {
  return useQuery({
    queryKey: computed(
      () =>
        [
          "inventory",
          ...scope.key.value,
          "write-off-execution-result",
          id.value,
        ] as const,
    ),
    queryFn: ({ queryKey, signal }) =>
      getWriteOffExecutionResult(queryKey[5], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 60000,
    retry: false,
  });
}
