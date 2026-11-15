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
  StatusChangeExecutionValues,
  StatusChangePostingResult,
} from "./status-change-posting.types";
import { statusChangePostingKeys } from "./status-change-posting.query-keys";
import { statusChangeKeys } from "./status-change.query-keys";
import { postStatusChange } from "../api/status-change-posting.api";
export interface PostStatusChangeInput {
  id: string;
  values: StatusChangeExecutionValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function usePostStatusChange(
  scope: InventoryScopeState,
): UseMutationReturnType<
  StatusChangePostingResult,
  Error,
  PostStatusChangeInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: PostStatusChangeInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((v, i) => v === scope.key.value[i]);
  return useMutation({
    mutationKey: computed(() => [
      ...statusChangePostingKeys.root(scope.key.value),
      "post",
    ]),
    retry: false,
    mutationFn: (
      input: PostStatusChangeInput,
    ): Promise<StatusChangePostingResult> => {
      if (!relevant(input))
        throw new Error("Контекст изменения состояния изменился.");
      return postStatusChange(input.id, input.values, input.key, input.signal);
    },
    onSuccess: async (_result, input) => {
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: stockAccountingKeys.root(input.scope),
      });
      await Promise.all([
        cache.invalidateQueries({
          queryKey: statusChangePostingKeys.root(input.scope),
        }),
        cache.invalidateQueries({
          queryKey: statusChangeKeys.detail(input.scope, input.id),
          exact: true,
          refetchType: "all",
        }),
        cache.invalidateQueries({
          queryKey: statusChangeKeys.lists(input.scope),
        }),
      ]);
    },
  });
}
