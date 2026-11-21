import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { IssueExecutionResult } from "./issue-execution-result.types";
import { getIssueExecutionResult } from "../api/issue-execution-result.api";
export function useIssueExecutionResult(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<IssueExecutionResult, Error> {
  return useQuery({
    queryKey: computed(
      () =>
        [
          "inventory",
          ...scope.key.value,
          "issue-execution-result",
          id.value,
        ] as const,
    ),
    queryFn: ({ queryKey, signal }) =>
      getIssueExecutionResult(queryKey[5], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 60000,
    retry: false,
  });
}
