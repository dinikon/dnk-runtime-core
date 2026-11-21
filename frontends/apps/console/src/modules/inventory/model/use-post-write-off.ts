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
  WriteOffExecutionValues,
  WriteOffPostingResult,
} from "./write-off-posting.types";
import { writeOffPostingKeys } from "./write-off-posting.query-keys";
import { writeOffKeys } from "./write-off.query-keys";
import { postWriteOff } from "../api/write-off-posting.api";
export interface PostWriteOffInput {
  id: string;
  values: WriteOffExecutionValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function usePostWriteOff(
  scope: InventoryScopeState,
): UseMutationReturnType<
  WriteOffPostingResult,
  Error,
  PostWriteOffInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: PostWriteOffInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((v, i) => v === scope.key.value[i]);
  return useMutation({
    mutationKey: computed(() => [
      ...writeOffPostingKeys.root(scope.key.value),
      "post",
    ]),
    retry: false,
    mutationFn: (input: PostWriteOffInput): Promise<WriteOffPostingResult> => {
      if (!relevant(input)) throw new Error("Контекст списания изменился.");
      return postWriteOff(input.id, input.values, input.key, input.signal);
    },
    onSuccess: async (_result, input) => {
      if (!relevant(input)) return;
      await cache.invalidateQueries({
        queryKey: stockAccountingKeys.root(input.scope),
      });
      await Promise.all([
        cache.invalidateQueries({
          queryKey: writeOffPostingKeys.root(input.scope),
        }),
        cache.invalidateQueries({
          queryKey: writeOffKeys.detail(input.scope, input.id),
          exact: true,
          refetchType: "all",
        }),
        cache.invalidateQueries({ queryKey: writeOffKeys.lists(input.scope) }),
      ]);
    },
  });
}
