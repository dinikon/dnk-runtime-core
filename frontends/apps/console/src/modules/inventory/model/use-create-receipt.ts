import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createReceipt } from "../api/receipt.api";
import { receiptKeys } from "./receipt.query-keys";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { ReceiptDocument, ReceiptDraftValues } from "./receipt.types";
export interface CreateReceiptInput {
  values: ReceiptDraftValues;
  key: string;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCreateReceipt(
  scope: InventoryScopeState,
): UseMutationReturnType<ReceiptDocument, Error, CreateReceiptInput, unknown> {
  const cache = useQueryClient();
  const relevant = (i: CreateReceiptInput): boolean =>
    scope.ready.value &&
    !i.signal.aborted &&
    i.scope.every((v, n) => v === scope.key.value[n]);
  return useMutation({
    mutationKey: computed(() => receiptKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateReceiptInput) => {
      if (!relevant(input)) throw new Error("Контекст поступления изменился.");
      return createReceipt(input.values, input.key, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: receiptKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData(receiptKeys.detail(input.scope, result.id), result);
      await cache.invalidateQueries({
        queryKey: receiptKeys.lists(input.scope),
      });
    },
  });
}
