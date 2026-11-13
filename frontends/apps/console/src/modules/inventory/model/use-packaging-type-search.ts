import {
  computed,
  onScopeDispose,
  ref,
  watch,
  type ComputedRef,
  type Ref,
} from "vue";
import { useInfiniteQuery } from "@tanstack/vue-query";
import { listPackagingTypes } from "../api/packaging-type.api";
import { packagingTypeKeys } from "./packaging-type.query-keys";
import { retryPackagingTypes } from "./packaging-type.errors";
import {
  PACKAGING_TYPE_MAX_OFFSET,
  PACKAGING_TYPE_SEARCH_DELAY,
} from "./packaging-type.constants";
import type { InventoryScopeState } from "./use-inventory-scope";
import type { PackagingType } from "./packaging-type.types";
export interface PackagingTypeSearch {
  search: Ref<string>;
  options: ComputedRef<readonly PackagingType[]>;
  total: ComputedRef<number>;
  loading: ComputedRef<boolean>;
  fetchingMore: ComputedRef<boolean>;
  hasMore: ComputedRef<boolean>;
  error: ComputedRef<string>;
  reset(): void;
  retry(): void;
  more(): void;
}
export function usePackagingTypeSearch(
  enabled: Ref<boolean>,
  scope: InventoryScopeState,
  resetKey: Ref<string>,
): PackagingTypeSearch {
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
      }, PACKAGING_TYPE_SEARCH_DELAY);
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
      packagingTypeKeys.candidates(
        scope.key.value,
        committed.value,
      ),
    ),
    initialPageParam: 0,
    queryFn: ({ queryKey, pageParam, signal }) =>
      listPackagingTypes(
        { ...queryKey[6], offset: pageParam },
        signal,
      ),
    getNextPageParam: (last) => {
      const offset = last.offset + last.limit;
      return offset < last.total && offset <= PACKAGING_TYPE_MAX_OFFSET
        ? offset
        : undefined;
    },
    enabled: computed(
      () => enabled.value && scope.ready.value,
    ),
    staleTime: 30_000,
    retry: retryPackagingTypes,
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
