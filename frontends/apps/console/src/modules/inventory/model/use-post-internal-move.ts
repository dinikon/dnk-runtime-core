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
  InternalMoveExecutionValues,
  InternalMovePostingResult,
} from "./internal-move-posting.types";
import { internalMovePostingKeys } from "./internal-move-posting.query-keys";
import { internalMoveKeys } from "./internal-move.query-keys";
import { postInternalMove } from "../api/internal-move-posting.api";
export interface PostInternalMoveInput {
  id: string;
  values: InternalMoveExecutionValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function usePostInternalMove(
  scope: InventoryScopeState,
): UseMutationReturnType<
  InternalMovePostingResult,
  Error,
  PostInternalMoveInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: PostInternalMoveInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((v, i) => v === scope.key.value[i]);
  return useMutation({
    mutationKey: computed(() => [
      ...internalMovePostingKeys.root(scope.key.value),
      "post",
    ]),
    retry: false,
    mutationFn: (
      input: PostInternalMoveInput,
    ): Promise<InternalMovePostingResult> => {
      if (!relevant(input)) throw new Error("Контекст перемещения изменился.");
      return postInternalMove(input.id, input.values, input.key, input.signal);
    },
    onSuccess: async (_result, input) => {
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: stockAccountingKeys.root(input.scope),
      });
      await Promise.all([
        cache.invalidateQueries({
          queryKey: internalMovePostingKeys.root(input.scope),
        }),
        cache.invalidateQueries({
          queryKey: internalMoveKeys.detail(input.scope, input.id),
          exact: true,
          refetchType: "all",
        }),
        cache.invalidateQueries({
          queryKey: internalMoveKeys.lists(input.scope),
        }),
      ]);
    },
  });
}
