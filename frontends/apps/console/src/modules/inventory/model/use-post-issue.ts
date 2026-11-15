import { stockAccountingKeys } from "./stock-accounting.query-keys";
import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import type {
  IssueExecutionValues,
  IssuePostingResult,
} from "./issue-posting.types";
import { issuePostingKeys } from "./issue-posting.query-keys";
import { issueKeys } from "./issue.query-keys";
import { postIssue } from "../api/issue-posting.api";
export interface PostIssueInput {
  id: string;
  values: IssueExecutionValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function usePostIssue(
  scope: InventoryScopeState,
): UseMutationReturnType<IssuePostingResult, Error, PostIssueInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: PostIssueInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((v, i) => v === scope.key.value[i]);
  return useMutation({
    mutationKey: computed(() => [
      ...issuePostingKeys.root(scope.key.value),
      "post",
    ]),
    retry: false,
    mutationFn: (input: PostIssueInput): Promise<IssuePostingResult> => {
      if (!relevant(input)) throw new Error("Контекст выдачи изменился.");
      return postIssue(input.id, input.values, input.key, input.signal);
    },
    onSuccess: async (_result, input) => {
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: stockAccountingKeys.root(input.scope),
      });
      await Promise.all([
        cache.invalidateQueries({
          queryKey: issuePostingKeys.root(input.scope),
        }),
        cache.invalidateQueries({
          queryKey: issueKeys.detail(input.scope, input.id),
          exact: true,
          refetchType: "all",
        }),
        cache.invalidateQueries({ queryKey: issueKeys.lists(input.scope) }),
      ]);
    },
  });
}
