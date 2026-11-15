import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchIssue } from "../api/issue.api";
import { issueKeys } from "./issue.query-keys";
import { newestIssue } from "./issue-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { IssueDocument, IssueEditValues } from "./issue.types";
export interface UpdateIssueInput {
  id: string;
  values: IssueEditValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useUpdateIssue(
  scope: InventoryScopeState,
): UseMutationReturnType<IssueDocument, Error, UpdateIssueInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: UpdateIssueInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => issueKeys.update(scope.key.value)),
    retry: false,
    mutationFn: (input: UpdateIssueInput): Promise<IssueDocument> => {
      if (!relevant(input)) throw new Error("Контекст расхода изменился.");
      return patchIssue(input.id, input.values, input.signal);
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
