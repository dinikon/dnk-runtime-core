import { stockLotDateDependency } from "./stock-lot-date-dependencies";
import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { getStockLot, listStockLots } from "../api/stock-lot.api";
import { stockLotKeys } from "./stock-lot.query-keys";
import { retryStockLots } from "./stock-lot.errors";
import type {
  StockLot,
  StockLotsPage,
  StockLotsListParams,
} from "./stock-lot.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export function useStockLotsQuery(
  itemId: Ref<string>,
  params: Ref<StockLotsListParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<StockLotsPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockLotKeys.list(scope.key.value, itemId.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listStockLots(queryKey[5], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!itemId.value),
    staleTime: 30_000,
    retry: retryStockLots,
  });
}
export function useStockLotQuery(
  itemId: Ref<string>,
  lotId: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<StockLot, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockLotKeys.detail(scope.key.value, itemId.value, lotId.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      getStockLot(queryKey[5], queryKey[7], signal),
    meta: computed(() => stockLotDateDependency(itemId.value, lotId.value)),
    enabled: computed(
      () => scope.ready.value && !!itemId.value && !!lotId.value,
    ),
    staleTime: 30_000,
    retry: retryStockLots,
  });
}
