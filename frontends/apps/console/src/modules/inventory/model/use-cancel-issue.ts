import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { cancelIssue } from "../api/issue.api";
import { issueKeys } from "./issue.query-keys";
import { newestIssue } from "./issue-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { IssueDocument, IssueVersionValues } from "./issue.types";
export interface CancelIssueInput {
  id: string;
  values: IssueVersionValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCancelIssue(
  scope: InventoryScopeState,
): UseMutationReturnType<IssueDocument, Error, CancelIssueInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: CancelIssueInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => issueKeys.cancel(scope.key.value)),
    retry: false,
    mutationFn: (input: CancelIssueInput): Promise<IssueDocument> => {
      if (!relevant(input)) throw new Error("Контекст расхода изменился.");
      return cancelIssue(input.id, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: issueKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData<IssueDocument>(
        issueKeys.detail(input.scope, result.id),
        (current) => newestIssue(current, result),
      );
      await cache.invalidateQueries({
        queryKey: issueKeys.lists(input.scope),
      });
    },
  });
}
