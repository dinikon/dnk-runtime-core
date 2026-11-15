import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import type {
  ReceiptIntakeValues,
  ReceiptPostingResult,
} from "./receipt-posting.types";
import { receiptPostingKeys } from "./receipt-posting.query-keys";
import { receiptKeys } from "./receipt.query-keys";
import { postReceipt } from "../api/receipt-posting.api";
export interface PostReceiptInput {
  id: string;
  values: ReceiptIntakeValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function usePostReceipt(
  scope: InventoryScopeState,
): UseMutationReturnType<
  ReceiptPostingResult,
  Error,
  PostReceiptInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: PostReceiptInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((v, i) => v === scope.key.value[i]);
  return useMutation({
    mutationKey: computed(() => receiptPostingKeys.post(scope.key.value)),
    retry: false,
    mutationFn: (input: PostReceiptInput): Promise<ReceiptPostingResult> => {
      if (!relevant(input)) throw new Error("Контекст приёмки изменился.");
      return postReceipt(input.id, input.values, input.key, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      cache.setQueryData(
        receiptPostingKeys.execution(input.scope, result.executionId),
        result,
      );
      cache.setQueryData(
        receiptPostingKeys.posting(input.scope, result.postingId),
        result,
      );
      await Promise.all([
        cache.invalidateQueries({
          queryKey: receiptKeys.detail(input.scope, input.id),
          exact: true,
          refetchType: "all",
        }),
        cache.invalidateQueries({ queryKey: receiptKeys.lists(input.scope) }),
        cache.invalidateQueries({
          queryKey: receiptPostingKeys.context(input.scope, input.id),
          exact: true,
        }),
        cache.invalidateQueries({
          queryKey: receiptPostingKeys
            .history(input.scope, input.id, 0)
            .slice(0, -1),
        }),
      ]);
    },
  });
}
