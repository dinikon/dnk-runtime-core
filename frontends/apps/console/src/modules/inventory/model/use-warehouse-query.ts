import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { getWarehouse } from "../api/warehouse.api";
import { warehouseKeys } from "./warehouse.query-keys";
import { retryWarehouses } from "./warehouse.errors";
import type { Warehouse } from "./warehouse.types";
import type { InventoryScopeState } from "./use-inventory-scope";

export function useWarehouseQuery(
  id: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<Warehouse, Error> {
  return useQuery({
    queryKey: computed(() => warehouseKeys.detail(scope.key.value, id.value)),
    queryFn: ({ queryKey, signal }) => getWarehouse(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && !!id.value),
    staleTime: 30_000,
    retry: retryWarehouses,
  });
}
