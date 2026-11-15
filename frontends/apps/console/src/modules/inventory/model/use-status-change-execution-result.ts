import { statusChangePostingKeys } from "./status-change-posting.query-keys";
import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { StatusChangeExecutionResult } from "./status-change-execution-result.types";
import { getStatusChangeExecutionResult } from "../api/status-change-execution-result.api";
export function useStatusChangeExecutionResult(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<StatusChangeExecutionResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      statusChangePostingKeys.result(scope.key.value, id.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      getStatusChangeExecutionResult(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 60000,
    retry: false,
  });
}
