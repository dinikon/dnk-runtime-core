import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { patchWarehouse } from "../api/warehouse.api";
import type { Warehouse, WarehouseChanges } from "./warehouse.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { warehouseKeys } from "./warehouse.query-keys";

export interface UpdateWarehouseInput {
  id: string;
  values: WarehouseChanges;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useUpdateWarehouse(
  scope: InventoryScopeState,
): UseMutationReturnType<Warehouse, Error, UpdateWarehouseInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: UpdateWarehouseInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => warehouseKeys.update(scope.key.value)),
    retry: false,
    mutationFn: (input: UpdateWarehouseInput) => {
      if (!relevant(input)) throw new Error("Контекст склада изменился.");
      return patchWarehouse(input.id, input.values, input.signal);
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      await cache.cancelQueries({
        queryKey: warehouseKeys.detail(input.scope, result.id),
        exact: true,
      });
      if (!relevant(input)) return;
      cache.setQueryData(warehouseKeys.detail(input.scope, result.id), result);
      await cache.invalidateQueries({
        queryKey: warehouseKeys.lists(input.scope),
      });
    },
  });
}
