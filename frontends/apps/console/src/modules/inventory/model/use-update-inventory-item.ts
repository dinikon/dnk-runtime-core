import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchInventoryItem } from "../api/inventory-item-edit.api";
import { InventoryItemWriteError } from "./inventory-item-write.errors";
import { discardInaccessibleInventoryItem } from "./inventory-item-removal";
import { itemPackagingKeys } from "./item-packaging.query-keys";
import { inventoryItemKeys } from "./inventory-item.query-keys";
import type { InventoryItemDetails } from "./inventory-item-settings.types";
import type {
  InventoryItemChanges,
  InventoryItemMutationInput,
} from "./inventory-item-editor.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export interface UpdateInventoryItemInput extends InventoryItemMutationInput {
  changes: InventoryItemChanges;
}
export function useUpdateInventoryItem(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<
  InventoryItemDetails,
  Error,
  UpdateInventoryItemInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: UpdateInventoryItemInput): boolean =>
    scope.ready.value &&
    input.id === id.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      inventoryItemKeys.update(scope.key.value, id.value),
    ),
    retry: false,
    mutationFn: (
      input: UpdateInventoryItemInput,
    ): Promise<InventoryItemDetails> => {
      if (!relevant(input))
        throw new Error("Контекст редактирования изменился.");
      return patchInventoryItem(input.id, input.changes, input.signal);
    },
    onError: async (error, input) => {
      if (
        error instanceof InventoryItemWriteError &&
        [403, 404].includes(error.status ?? 0)
      )
        await discardInaccessibleInventoryItem(cache, input, () =>
          relevant(input),
        );
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await Promise.all([
        cache.cancelQueries({
          queryKey: inventoryItemKeys.detail(input.scope, input.id),
          exact: true,
        }),
        cache.cancelQueries({ queryKey: inventoryItemKeys.lists(input.scope) }),
      ]);
      if (!relevant(input)) return;
      cache.setQueryData(
        inventoryItemKeys.detail(input.scope, input.id),
        result,
      );
      await Promise.all([
        cache.invalidateQueries({
          queryKey: inventoryItemKeys.lists(input.scope),
        }),
        cache.invalidateQueries({
          queryKey: itemPackagingKeys.root(input.scope, input.id),
        }),
      ]);
    },
  });
}
