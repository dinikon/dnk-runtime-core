import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { ItemPackagingRequestError } from "./item-packaging.errors";
import { createItemPackaging } from "../api/item-packaging.api";
import { itemPackagingKeys } from "./item-packaging.query-keys";
import type {
  ItemPackaging,
  ItemPackagingValues,
} from "./item-packaging.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export interface CreateItemPackagingInput {
  itemId: string;
  scope: InventoryScope;
  signal: AbortSignal;
  values: ItemPackagingValues;
}
export function useCreateItemPackaging(
  itemId: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<
  ItemPackaging,
  Error,
  CreateItemPackagingInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: CreateItemPackagingInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.itemId === itemId.value &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      itemPackagingKeys.create(scope.key.value, itemId.value),
    ),
    retry: false,
    mutationFn: (input: CreateItemPackagingInput) => {
      if (!relevant(input)) throw new Error("Контекст упаковки изменился.");
      return createItemPackaging(input.itemId, input.values, input.signal);
    },
    onError: async (error, input) => {
      if (
        relevant(input) &&
        (!(error instanceof ItemPackagingRequestError) || error.uncertain)
      )
        await cache.invalidateQueries({
          queryKey: itemPackagingKeys.lists(input.scope, input.itemId),
        });
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
