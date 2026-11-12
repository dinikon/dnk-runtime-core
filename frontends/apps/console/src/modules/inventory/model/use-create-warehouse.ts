import { computed } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { createWarehouse } from "../api/warehouse.api";
import type { Warehouse, WarehouseCreateValues } from "./warehouse.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { warehouseKeys } from "./warehouse.query-keys";

export interface CreateWarehouseInput {
  values: WarehouseCreateValues;
  scope: InventoryScope;
  signal: AbortSignal;
}
export function useCreateWarehouse(
  scope: InventoryScopeState,
): UseMutationReturnType<Warehouse, Error, CreateWarehouseInput, unknown> {
  const cache = useQueryClient();
  const relevant = (input: CreateWarehouseInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() => warehouseKeys.create(scope.key.value)),
    retry: false,
    mutationFn: (input: CreateWarehouseInput) => {
      if (!relevant(input)) throw new Error("Контекст склада изменился.");
      return createWarehouse(input.values, input.signal);
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
