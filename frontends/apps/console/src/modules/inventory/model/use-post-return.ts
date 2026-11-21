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
  ReturnExecutionValues,
  ReturnPostingResult,
} from "./return-posting.types";
import { returnPostingKeys } from "./return-posting.query-keys";
import { returnKeys } from "./return.query-keys";
import { postReturn } from "../api/return-posting.api";
export interface PostReturnInput {
  id: string;
  values: ReturnExecutionValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function usePostReturn(
  scope: InventoryScopeState,
): UseMutationReturnType<ReturnPostingResult, Error, PostReturnInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: PostReturnInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((v, i) => v === scope.key.value[i]);
  return useMutation({
    mutationKey: computed(() => [
      ...returnPostingKeys.root(scope.key.value),
      "post",
    ]),
    retry: false,
    mutationFn: (input: PostReturnInput): Promise<ReturnPostingResult> => {
      if (!relevant(input)) throw new Error("Контекст возврата изменился.");
      return postReturn(input.id, input.values, input.key, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: stockAccountingKeys.root(input.scope),
      });
      await Promise.all([
        cache.invalidateQueries({
          queryKey: returnKeys.origin(input.scope, result.originExecutionId),
        }),
        cache.invalidateQueries({
          queryKey: returnPostingKeys.root(input.scope),
        }),
        cache.invalidateQueries({
          queryKey: returnKeys.detail(input.scope, input.id),
          exact: true,
          refetchType: "all",
        }),
        cache.invalidateQueries({
          queryKey: returnKeys.lists(input.scope),
        }),
      ]);
    },
  });
}
