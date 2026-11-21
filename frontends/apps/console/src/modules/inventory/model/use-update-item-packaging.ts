import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchItemPackaging } from "../api/item-packaging.api";
import { itemPackagingKeys } from "./item-packaging.query-keys";
import type {
  ItemPackaging,
  ItemPackagingChanges,
} from "./item-packaging.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export interface UpdateItemPackagingInput {
  itemId: string;
  id: string;
  scope: InventoryScope;
  signal: AbortSignal;
  values: ItemPackagingChanges;
}
export function useUpdateItemPackaging(
  itemId: Ref<string>,
  id: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<
  ItemPackaging,
  Error,
  UpdateItemPackagingInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: UpdateItemPackagingInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.itemId === itemId.value &&
    input.id === id.value &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      itemPackagingKeys.update(scope.key.value, itemId.value, id.value),
    ),
    retry: false,
    mutationFn: (input: UpdateItemPackagingInput) => {
      if (!relevant(input)) throw new Error("Контекст упаковки изменился.");
      return patchItemPackaging(
        input.itemId,
        input.id,
        input.values,
        input.signal,
      );
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: itemPackagingKeys.detail(
          input.scope,
          input.itemId,
          result.id,
        ),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData(
        itemPackagingKeys.detail(input.scope, input.itemId, result.id),
        result,
      );
      await cache.invalidateQueries({
        queryKey: itemPackagingKeys.lists(input.scope, input.itemId),
      });
    },
  });
}
