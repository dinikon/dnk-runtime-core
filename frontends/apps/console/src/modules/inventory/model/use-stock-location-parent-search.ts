import {
  computed,
  onScopeDispose,
  ref,
  watch,
  type ComputedRef,
  type Ref,
} from "vue";
import { useInfiniteQuery } from "@tanstack/vue-query";
import { listStockLocations } from "../api/stock-location.api";
import { stockLocationKeys } from "./stock-location.query-keys";
import { retryStockLocations } from "./stock-location.errors";
import {
  STOCK_LOCATION_MAX_OFFSET,
  STOCK_LOCATION_SEARCH_DELAY,
} from "./stock-location.constants";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { StockLocation } from "./stock-location.types";
export interface StockLocationParentSearch {
  search: Ref<string>;
  options: ComputedRef<readonly StockLocation[]>;
  total: ComputedRef<number>;
  loading: ComputedRef<boolean>;
  fetchingMore: ComputedRef<boolean>;
  hasMore: ComputedRef<boolean>;
  error: ComputedRef<string>;
  reset(): void;
  retry(): void;
  more(): void;
}
export function useStockLocationParentSearch(
  warehouseId: Ref<string>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
  resetKey: Ref<string>,
): StockLocationParentSearch {
  const search = ref(""),
    committed = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined;
  function cancel(): void {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }
  function reset(): void {
    search.value = "";
    committed.value = "";
    cancel();
  }
  watch(
    search,
    (value) => {
      cancel();
      timer = setTimeout(() => {
        committed.value = value.trim();
      }, STOCK_LOCATION_SEARCH_DELAY);
    },
    { flush: "sync" },
  );
  watch(resetKey, reset, { flush: "sync" });
  watch(
    enabled,
    (value) => {
      if (!value) reset();
    },
    { flush: "sync" },
  );
  onScopeDispose(cancel);
  const query = useInfiniteQuery({
    queryKey: computed(() =>
      stockLocationKeys.parents(
        scope.key.value,
        warehouseId.value,
        committed.value,
      ),
    ),
    initialPageParam: 0,
    queryFn: ({ queryKey, pageParam, signal }) =>
      listStockLocations(
        queryKey[5],
        { ...queryKey[7], offset: pageParam },
        signal,
      ),
    getNextPageParam: (last) => {
      const offset = last.offset + last.limit;
      return offset < last.total && offset <= STOCK_LOCATION_MAX_OFFSET
        ? offset
        : undefined;
    },
    enabled: computed(
      () => enabled.value && scope.ready.value && !!warehouseId.value,
    ),
    staleTime: 30_000,
    retry: retryStockLocations,
  });
  const loading = computed(
    () =>
      enabled.value &&
      (search.value.trim() !== committed.value || query.isPending.value),
  );
  return {
    search,
    options: computed(() =>
      loading.value
        ? []
        : [
            ...new Map(
              (query.data.value?.pages.flatMap((page) => page.items) ?? []).map(
                (item) => [item.id, item],
              ),
            ).values(),
          ],
    ),
    total: computed(() => query.data.value?.pages[0]?.total ?? 0),
    loading,
    fetchingMore: computed(() => query.isFetching.value && !loading.value),
    hasMore: computed(() => !!query.hasNextPage.value),
    error: computed(() => query.error.value?.message || ""),
    reset,
    retry: () => {
      if (enabled.value && scope.ready.value) void query.refetch();
    },
    more: () => {
      if (
        enabled.value &&
        scope.ready.value &&
        query.hasNextPage.value &&
        !query.isFetching.value &&
        search.value.trim() === committed.value
      )
        void query.fetchNextPage();
    },
  };
}
