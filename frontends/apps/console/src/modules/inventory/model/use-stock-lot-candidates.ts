import {
  computed,
  ref,
  watch,
  onScopeDispose,
  type Ref,
  type ComputedRef,
} from "vue";
import { useInfiniteQuery } from "@tanstack/vue-query";
import { listStockLots } from "../api/stock-lot.api";
import { stockLotKeys } from "./stock-lot.query-keys";
import { retryStockLots } from "./stock-lot.errors";
import type { StockLot } from "./stock-lot.types";
import type { InventoryScopeState } from "./use-inventory-scope";
interface StockLotCandidates {
  search: Ref<string>;
  items: ComputedRef<StockLot[]>;
  error: ComputedRef<string>;
  pending: ComputedRef<boolean>;
  refreshing: ComputedRef<boolean>;
  hasMore: ComputedRef<boolean>;
  setSearch(value: string): void;
  reset(): void;
  more(): Promise<void>;
  retry(): Promise<void>;
}
export function useStockLotCandidates(
  itemId: Ref<string>,
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
): StockLotCandidates {
  const search = ref(""),
    settled = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined;
  function cancel(): void {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }
  function reset(): void {
    cancel();
    search.value = "";
    settled.value = "";
  }
  function setSearch(value: string): void {
    search.value = value;
    cancel();
    timer = setTimeout(() => {
      settled.value = value.trim();
      timer = undefined;
    }, 300);
  }
  const query = useInfiniteQuery({
    queryKey: computed(() =>
      stockLotKeys.candidates(scope.key.value, itemId.value, settled.value),
    ),
    queryFn: ({ queryKey, signal, pageParam }) =>
      listStockLots(
        queryKey[5],
        { search: queryKey[7], offset: pageParam, limit: 20 },
        signal,
      ),
    initialPageParam: 0,
    getNextPageParam: (last) =>
      last.offset + last.items.length < last.total && last.items.length
        ? last.offset + last.items.length
        : undefined,
    enabled: computed(
      () => scope.ready.value && !!itemId.value && enabled.value,
    ),
    retry: retryStockLots,
    staleTime: 15_000,
  });
  watch(
    () =>
      JSON.stringify([
        ...scope.key.value,
        scope.ready.value,
        itemId.value,
        enabled.value,
      ]),
    reset,
    { flush: "sync" },
  );
  onScopeDispose(cancel);
  return {
    search,
    setSearch,
    reset,
    items: computed(
      () => query.data.value?.pages.flatMap((page) => page.items) ?? [],
    ),
    error: computed(() => query.error.value?.message ?? ""),
    pending: computed(() => query.isPending.value && enabled.value),
    refreshing: computed(() => query.isFetching.value),
    hasMore: computed(() => query.hasNextPage.value),
    more: async () => {
      if (!query.isFetching.value && query.hasNextPage.value)
        await query.fetchNextPage();
    },
    retry: async () => {
      await query.refetch();
    },
  };
}
