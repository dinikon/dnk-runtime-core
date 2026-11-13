import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchStockLocation } from "../api/stock-location.api";
import type {
  StockLocation,
  StockLocationChanges,
} from "./stock-location.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { stockLocationKeys } from "./stock-location.query-keys";
export interface UpdateStockLocationInput {
  warehouseId: string;
  id: string;
  values: StockLocationChanges;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useUpdateStockLocation(
  warehouseId: Ref<string>,
  id: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<
  StockLocation,
  Error,
  UpdateStockLocationInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: UpdateStockLocationInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.warehouseId === warehouseId.value &&
    input.id === id.value &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      stockLocationKeys.update(scope.key.value, warehouseId.value),
    ),
    retry: false,
    mutationFn: (input: UpdateStockLocationInput) => {
      if (!relevant(input)) throw new Error("Контекст локации изменился.");
      return patchStockLocation(
        input.warehouseId,
        input.id,
        input.values,
        input.signal,
      );
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      const key = stockLocationKeys.detail(
        input.scope,
        input.warehouseId,
        result.id,
      );
      await cache.cancelQueries({ queryKey: key, exact: true });
      if (!relevant(input)) return;
      cache.setQueryData(key, result);
      await Promise.all([
        cache.invalidateQueries({
          queryKey: stockLocationKeys.lists(input.scope, input.warehouseId),
        }),
        cache.invalidateQueries({
          queryKey: stockLocationKeys.parentSearches(
            input.scope,
            input.warehouseId,
          ),
        }),
      ]);
    },
  });
}
