import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { deleteItemPackaging } from "../api/item-packaging.api";
import { itemPackagingKeys } from "./item-packaging.query-keys";
import {
  forgetItemPackaging,
  type DeleteItemPackagingInput,
} from "./item-packaging-removal";
import type { InventoryScopeState } from "./use-inventory-scope";

export function useDeleteItemPackaging(
  itemId: Ref<string>,
  id: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<void, Error, DeleteItemPackagingInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: DeleteItemPackagingInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.itemId === itemId.value &&
    input.id === id.value &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      itemPackagingKeys.delete(scope.key.value, itemId.value, id.value),
    ),
    retry: false,
    mutationFn: (input: DeleteItemPackagingInput): Promise<void> => {
      if (!relevant(input)) throw new Error("Контекст упаковки изменился.");
      return deleteItemPackaging(input.itemId, input.id, input.signal);
    },
    onSuccess: (_, input) =>
      forgetItemPackaging(cache, input, () => relevant(input)),
  });
}
