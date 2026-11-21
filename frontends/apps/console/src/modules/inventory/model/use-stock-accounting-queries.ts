import type {
  StockBalancesParams,
  ListStockBalancesResult,
} from "./stock-accounting.types";
import { listStockBalances } from "../api/stock-accounting.api";
import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import type { InventoryScopeState } from "./use-inventory-scope";
import type {
  StockReadParams,
  ListStockPositionsResult,
  GetStockPositionResult,
  ListStockMovementsResult,
  ListStockExecutionsResult,
  ListStockPostingsResult,
  GetStockExecutionDetailsResult,
  GetStockPostingDetailsResult,
} from "./stock-accounting.types";
import {
  listStockPositions,
  getStockPosition,
  listStockMovements,
  listStockExecutions,
  listStockPostings,
  getStockExecutionDetails,
  getStockPostingDetails,
} from "../api/stock-accounting.api";
import { stockAccountingKeys } from "./stock-accounting.query-keys";
export function useListStockPositions(
  value: Ref<StockReadParams>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): UseQueryReturnType<ListStockPositionsResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockAccountingKeys.listStockPositions(scope.key.value, value.value),
    ),
    queryFn: ({ queryKey, signal }) => listStockPositions(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && enabled.value),
    staleTime: 0,
    retry: false,
  });
}
export function useGetStockPosition(
  value: Ref<string>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): UseQueryReturnType<GetStockPositionResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockAccountingKeys.getStockPosition(scope.key.value, value.value),
    ),
    queryFn: ({ queryKey, signal }) => getStockPosition(queryKey[6], signal),
    enabled: computed(
      () => scope.ready.value && enabled.value && !!value.value,
    ),
    staleTime: 0,
    retry: false,
  });
}
export function useListStockMovements(
  value: Ref<StockReadParams>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): UseQueryReturnType<ListStockMovementsResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockAccountingKeys.listStockMovements(scope.key.value, value.value),
    ),
    queryFn: ({ queryKey, signal }) => listStockMovements(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && enabled.value),
    staleTime: 0,
    retry: false,
  });
}
export function useListStockExecutions(
  value: Ref<StockReadParams>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): UseQueryReturnType<ListStockExecutionsResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockAccountingKeys.listStockExecutions(scope.key.value, value.value),
    ),
    queryFn: ({ queryKey, signal }) => listStockExecutions(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && enabled.value),
    staleTime: 0,
    retry: false,
  });
}
export function useListStockPostings(
  value: Ref<StockReadParams>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): UseQueryReturnType<ListStockPostingsResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockAccountingKeys.listStockPostings(scope.key.value, value.value),
    ),
    queryFn: ({ queryKey, signal }) => listStockPostings(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && enabled.value),
    staleTime: 0,
    retry: false,
  });
}
export function useGetStockExecutionDetails(
  value: Ref<string>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): UseQueryReturnType<GetStockExecutionDetailsResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockAccountingKeys.getStockExecutionDetails(
        scope.key.value,
        value.value,
      ),
    ),
    queryFn: ({ queryKey, signal }) =>
      getStockExecutionDetails(queryKey[6], signal),
    enabled: computed(
      () => scope.ready.value && enabled.value && !!value.value,
    ),
    staleTime: 0,
    retry: false,
  });
}
export function useGetStockPostingDetails(
  value: Ref<string>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): UseQueryReturnType<GetStockPostingDetailsResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockAccountingKeys.getStockPostingDetails(scope.key.value, value.value),
    ),
    queryFn: ({ queryKey, signal }) =>
      getStockPostingDetails(queryKey[6], signal),
    enabled: computed(
      () => scope.ready.value && enabled.value && !!value.value,
    ),
    staleTime: 0,
    retry: false,
  });
}

export function useListStockBalances(
  value: Ref<StockBalancesParams>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): UseQueryReturnType<ListStockBalancesResult, Error> {
  return useQuery({
    queryKey: computed(() =>
      stockAccountingKeys.listStockBalances(scope.key.value, value.value),
    ),
    queryFn: ({ queryKey, signal }) => listStockBalances(queryKey[6], signal),
    enabled: computed(() => scope.ready.value && enabled.value),
    staleTime: 0,
    retry: false,
  });
}
