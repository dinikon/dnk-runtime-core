import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchInventoryItemSettings } from "../api/inventory-item-settings.api";
import { itemPackagingKeys } from "./item-packaging.query-keys";
import { inventoryItemKeys } from "./inventory-item.query-keys";
import type {
  InventoryItemDetails,
  InventoryItemSettings,
} from "./inventory-item-settings.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";

export interface UpdateInventoryItemSettingsInput {
  id: string;
  scope: InventoryScope;
  settings: InventoryItemSettings;
  signal: AbortSignal;
}

export function useUpdateInventoryItemSettings(
  scope: InventoryScopeState,
): UseMutationReturnType<
  InventoryItemDetails,
  Error,
  UpdateInventoryItemSettingsInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: UpdateInventoryItemSettingsInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => inventoryItemKeys.settings(scope.key.value)),
    retry: false,
    mutationFn: (input: UpdateInventoryItemSettingsInput) => {
      if (!relevant(input))
        throw new Error("Контекст редактирования изменился.");
      return patchInventoryItemSettings(input.id, input.settings, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      // An older in-flight read must not replace the acknowledged PATCH result.
      await cache.cancelQueries({
        queryKey: inventoryItemKeys.detail(input.scope, input.id),
        exact: true,
      });
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
