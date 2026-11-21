import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { IssuesPage, IssuesParams } from "./issue.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { issueKeys } from "./issue.query-keys";
import { listIssues } from "../api/issue.api";
export function useIssuesQuery(
  params: Ref<IssuesParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<IssuesPage, Error> {
  return useQuery({
    queryKey: computed(() => issueKeys.list(scope.key.value, params.value)),
    queryFn: ({ queryKey, signal }) => listIssues(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: false,
  });
}
