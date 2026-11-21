import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { listStockLocations } from "../api/stock-location.api";
import type {
  StockLocationsListParams,
  StockLocationsPage,
} from "./stock-location.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { stockLocationKeys } from "./stock-location.query-keys";
import { retryStockLocations } from "./stock-location.errors";
export function useStockLocationsQuery(
  warehouseId: Ref<string>,
  params: Ref<StockLocationsListParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<StockLocationsPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockLocationKeys.list(scope.key.value, warehouseId.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listStockLocations(queryKey[5], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!warehouseId.value),
    staleTime: 30_000,
    retry: retryStockLocations,
  });
}
