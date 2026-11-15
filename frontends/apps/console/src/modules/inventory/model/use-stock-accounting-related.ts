import { StockAccountingRequestError } from "../api/stock-accounting.api";
import type { UseQueryReturnType } from "@tanstack/vue-query";
import type {
  ListStockBalancesResult,
  ListStockMovementsResult,
} from "./stock-accounting.types";
import { computed, ref, watch, type Ref, type ComputedRef } from "vue";
import type { StockFilters } from "./stock-accounting.types";
import type { InventoryScopeState } from "./use-inventory-scope";
import {
  useListStockBalances,
  useListStockMovements,
} from "./use-stock-accounting-queries";
export interface StockAccountingRelatedState {
  positionsData: ComputedRef<ListStockBalancesResult | undefined>;
  movementsData: ComputedRef<ListStockMovementsResult | undefined>;
  columns: Ref<{ lot: boolean; serial: boolean }>;
  positions: UseQueryReturnType<ListStockBalancesResult, Error>;
  movements: UseQueryReturnType<ListStockMovementsResult, Error>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  retry(): void;
}
export function useStockAccountingRelated(
  filters: Ref<StockFilters>,
  scope: InventoryScopeState,
  enabled: Ref<boolean>,
): StockAccountingRelatedState {
  const columns = ref({ lot: false, serial: false });
  watch(
    () => JSON.stringify([filters.value, ...scope.key.value]),
    () => {
      columns.value = { lot: false, serial: false };
    },
  );
  const params = computed(() => ({
    filters: filters.value,
    offset: 0,
    limit: 5,
  }));
  const balanceParams = computed(() => ({
    ...params.value,
    groupByLot: columns.value.lot,
    groupBySerial: columns.value.serial,
  }));
  const positions = useListStockBalances(balanceParams, scope, enabled),
    movements = useListStockMovements(params, scope, enabled);
  const loading = computed(
    () =>
      enabled.value && (positions.isPending.value || movements.isPending.value),
  );
  const error = computed(
    () =>
      positions.error.value?.message || movements.error.value?.message || "",
  );
  function retry(): void {
    void positions.refetch();
    void movements.refetch();
  }
  const positionsData = computed(() =>
    scope.ready.value &&
    enabled.value &&
    !(
      positions.error.value instanceof StockAccountingRequestError &&
      [403, 404].includes(positions.error.value.status ?? 0)
    )
      ? positions.data.value
      : undefined,
  );
  const movementsData = computed(() =>
    scope.ready.value &&
    enabled.value &&
    !(
      movements.error.value instanceof StockAccountingRequestError &&
      [403, 404].includes(movements.error.value.status ?? 0)
    )
      ? movements.data.value
      : undefined,
  );
  return {
    positionsData,
    movementsData,
    columns,
    positions,
    movements,
    loading,
    error,
    retry,
  };
}
