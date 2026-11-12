import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createInventoryItem } from "../api/inventory-item-create.api";
import type { CreateInventoryItemValues } from "./inventory-item-create.types";
import type { InventoryItemDetails } from "./inventory-item-settings.types";
import type { InventoryScope } from "./inventory-item.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { inventoryItemKeys } from "./inventory-item.query-keys";
import { InventoryItemCreateError } from "./inventory-item-create.errors";

export interface CreateInventoryItemInput {
  values: CreateInventoryItemValues;
  scope: InventoryScope;
  signal: AbortSignal;
}

export function useCreateInventoryItem(
  scope: InventoryScopeState,
): UseMutationReturnType<
  InventoryItemDetails,
  Error,
  CreateInventoryItemInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: CreateInventoryItemInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((value, index) => value === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => inventoryItemKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateInventoryItemInput) => {
      if (!relevant(input)) throw new Error("Контекст создания изменился.");
      return createInventoryItem(input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      cache.setQueryData(
        inventoryItemKeys.detail(input.scope, result.id),
        result,
      );
      await cache.invalidateQueries({
        queryKey: inventoryItemKeys.lists(input.scope),
      });
    },
    onError: async (error, input) => {
      if (
        relevant(input) &&
        error instanceof InventoryItemCreateError &&
        error.uncertain
      )
        await cache.invalidateQueries({
          queryKey: inventoryItemKeys.lists(input.scope),
          refetchType: "none",
        });
    },
  });
}
