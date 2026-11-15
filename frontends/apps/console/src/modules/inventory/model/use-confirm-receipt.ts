import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { confirmReceipt } from "../api/receipt.api";
import { receiptKeys } from "./receipt.query-keys";
import { newestReceipt } from "./receipt-edit";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { InventoryScope } from "./inventory-scope.types";
import type { ReceiptDocument, ReceiptVersionValues } from "./receipt.types";
export interface ConfirmReceiptInput {
  id: string;
  values: ReceiptVersionValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useConfirmReceipt(
  scope: InventoryScopeState,
): UseMutationReturnType<ReceiptDocument, Error, ConfirmReceiptInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: ConfirmReceiptInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => receiptKeys.confirm(scope.key.value)),
    retry: false,
    mutationFn: (input: ConfirmReceiptInput): Promise<ReceiptDocument> => {
      if (!relevant(input)) throw new Error("Контекст поступления изменился.");
      return confirmReceipt(input.id, input.values, input.signal);
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
