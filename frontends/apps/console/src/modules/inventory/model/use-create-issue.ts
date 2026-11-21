import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createIssue } from "../api/issue.api";
import { issueKeys } from "./issue.query-keys";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { IssueDocument, IssueDraftValues } from "./issue.types";
export interface CreateIssueInput {
  values: IssueDraftValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCreateIssue(
  scope: InventoryScopeState,
): UseMutationReturnType<IssueDocument, Error, CreateIssueInput, unknown> {
  const cache = useQueryClient();
  const relevant = (i: CreateIssueInput): boolean =>
    scope.ready.value &&
    !i.signal.aborted &&
    i.scope.every((v, n) => v === scope.key.value[n]);
  return useMutation({
    mutationKey: computed(() => issueKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateIssueInput) => {
      if (!relevant(input)) throw new Error("Контекст расхода изменился.");
      return createIssue(input.values, input.key, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      // Ответ идемпотентного создания может описывать прежнюю версию плана.
      await cache.invalidateQueries({
        queryKey: issueKeys.detail(input.scope, result.id),
        exact: true,
        refetchType: "all",
      });
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: issueKeys.lists(input.scope),
      });
    },
  });
}
