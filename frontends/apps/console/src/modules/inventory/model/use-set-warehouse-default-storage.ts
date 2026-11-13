import { computed, type Ref } from "vue";
import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { setWarehouseDefaultStorage } from "../api/warehouse-default-storage.api";
import type { Warehouse } from "./warehouse.types";
import type { WarehouseDefaultStorageValues } from "./warehouse-default-storage.types";
import type { InventoryScope } from "./inventory-scope.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { warehouseKeys } from "./warehouse.query-keys";

export interface SetWarehouseDefaultStorageInput {
  warehouseId: string;
  values: WarehouseDefaultStorageValues;
  scope: InventoryScope;
  signal: AbortSignal;
}

export function useSetWarehouseDefaultStorage(
  warehouseId: Ref<string>,
  scope: InventoryScopeState,
): UseMutationReturnType<
  Warehouse,
  Error,
  SetWarehouseDefaultStorageInput,
  unknown
> {
  const cache = useQueryClient();
  const relevant = (input: SetWarehouseDefaultStorageInput): boolean =>
    scope.ready.value &&
    !input.signal.aborted &&
    input.warehouseId === warehouseId.value &&
    input.scope.every((part, index) => part === scope.key.value[index]);
  return useMutation({
    mutationKey: computed(() =>
      warehouseKeys.setDefaultStorage(scope.key.value, warehouseId.value),
    ),
    retry: false,
    mutationFn: (input: SetWarehouseDefaultStorageInput) => {
      if (!relevant(input)) throw new Error("Контекст склада изменился.");
      return setWarehouseDefaultStorage(
        input.warehouseId,
        input.values,
        input.signal,
      );
    },
    onSuccess: async (result, input) => {
      if (!relevant(input)) return;
      const key = warehouseKeys.detail(input.scope, input.warehouseId);
      await cache.cancelQueries({ queryKey: key, exact: true });
      if (!relevant(input)) return;
      cache.setQueryData(key, result);
      await cache.invalidateQueries({
        queryKey: warehouseKeys.lists(input.scope),
      });
    },
  });
}
