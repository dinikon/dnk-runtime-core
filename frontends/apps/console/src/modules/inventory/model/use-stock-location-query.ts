import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { getStockLocation } from "../api/stock-location.api";
import type { StockLocation } from "./stock-location.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import { stockLocationKeys } from "./stock-location.query-keys";
import { retryStockLocations } from "./stock-location.errors";
export function useStockLocationQuery(
  warehouseId: Ref<string>,
  id: Ref<string | null>,
  scope: InventoryScopeState,
): UseQueryReturnType<StockLocation, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockLocationKeys.detail(
        scope.key.value,
        warehouseId.value,
        id.value ?? "",
      ),
    ),
    queryFn: ({ queryKey, signal }) =>
      getStockLocation(queryKey[5], queryKey[7], signal),
    enabled: computed(
      () => scope.ready.value && !!warehouseId.value && !!id.value,
    ),
    staleTime: 30_000,
    retry: retryStockLocations,
  });
}
