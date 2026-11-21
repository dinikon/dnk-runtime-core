import { stockLotDateDependency } from "./stock-lot-date-dependencies";
import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { getStockSerial, listStockSerials } from "../api/stock-serial.api";
import { stockSerialKeys } from "./stock-serial.query-keys";
import { retryStockSerials } from "./stock-serial.errors";
import type {
  StockSerial,
  StockSerialsPage,
  StockSerialsListParams,
} from "./stock-serial.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export function useStockSerialsQuery(
  itemId: Ref<string>,
  params: Ref<StockSerialsListParams>,
  scope: InventoryScopeState,
): UseQueryReturnType<StockSerialsPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockSerialKeys.list(scope.key.value, itemId.value, params.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      listStockSerials(queryKey[5], queryKey[7], signal),
    enabled: computed(() => scope.ready.value && !!itemId.value),
    meta: computed(() => stockLotDateDependency(itemId.value)),
    staleTime: 30_000,
    retry: retryStockSerials,
  });
}
export function useStockSerialQuery(
  itemId: Ref<string>,
  serialId: Ref<string>,
  scope: InventoryScopeState,
): UseQueryReturnType<StockSerial, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockSerialKeys.detail(scope.key.value, itemId.value, serialId.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      getStockSerial(queryKey[5], queryKey[7], signal),
    meta: computed(() => stockLotDateDependency(itemId.value)),
    enabled: computed(
      () => scope.ready.value && !!itemId.value && !!serialId.value,
    ),
    staleTime: 30_000,
    retry: retryStockSerials,
  });
}
