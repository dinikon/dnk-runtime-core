import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchReceipt } from "../api/receipt.api";
import { receiptKeys } from "./receipt.query-keys";
import { newestReceipt } from "./receipt-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { ReceiptDocument, ReceiptEditValues } from "./receipt.types";
export interface UpdateReceiptInput {
  id: string;
  values: ReceiptEditValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useUpdateReceipt(
  scope: InventoryScopeState,
): UseMutationReturnType<ReceiptDocument, Error, UpdateReceiptInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: UpdateReceiptInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => receiptKeys.update(scope.key.value)),
    retry: false,
    mutationFn: (input: UpdateReceiptInput): Promise<ReceiptDocument> => {
      if (!relevant(input)) throw new Error("Контекст поступления изменился.");
      return patchReceipt(input.id, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: receiptKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData<ReceiptDocument>(
        receiptKeys.detail(input.scope, result.id),
        (current) => newestReceipt(current, result),
      );
      await cache.invalidateQueries({
        queryKey: receiptKeys.lists(input.scope),
      });
    },
  });
}
