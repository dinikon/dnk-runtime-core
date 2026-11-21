import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { listWarehouses } from "../api/warehouse.api";
import { warehouseKeys } from "./warehouse.query-keys";
import { retryWarehouses } from "./warehouse.errors";
import type { WarehousesListParams, WarehousesPage } from "./warehouse.types";
import type { InventoryScopeState } from "./use-inventory-scope";

export function useWarehousesQuery(
  params: Ref<WarehousesListParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<WarehousesPage, Error> {
  return useQuery({
    queryKey: computed(() => warehouseKeys.list(scope.key.value, params.value)),
    queryFn: ({ queryKey, signal }) => listWarehouses(queryKey[6], signal),
    enabled: scope.ready,
    staleTime: 30_000,
    retry: retryWarehouses,
  });
}
