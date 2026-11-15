import { returnPostingKeys } from "./return-posting.query-keys";
import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { ReturnExecutionResult } from "./return-execution-result.types";
import { getReturnExecutionResult } from "../api/return-execution-result.api";
export function useReturnExecutionResult(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<ReturnExecutionResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      returnPostingKeys.result(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      getReturnExecutionResult(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 60000,
    retry: false,
  });
}
