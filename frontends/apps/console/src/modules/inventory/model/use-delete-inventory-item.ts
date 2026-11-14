import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { deleteInventoryItem } from "../api/inventory-item-edit.api";
import { inventoryItemKeys } from "./inventory-item.query-keys";
import { forgetInventoryItem } from "./inventory-item-removal";
import type { InventoryItemMutationInput } from "./inventory-item-editor.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export function useDeleteInventoryItem(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<void, Error, InventoryItemMutationInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: InventoryItemMutationInput): boolean =>
    scope.ready.value &&
    input.id === id.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      inventoryItemKeys.delete(scope.key.value, id.value),
    ),
    retry: false,
    mutationFn: (input: InventoryItemMutationInput): Promise<void> => {
      if (!relevant(input)) throw new Error("Контекст позиции изменился.");
      return deleteInventoryItem(input.id, input.signal);
    },
    onSuccess: (_, input) =>
      forgetInventoryItem(cache, input, () => relevant(input)),
  });
}
