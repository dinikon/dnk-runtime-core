import {
  computed,
  onScopeDispose,
  ref,
  watch,
  type Ref,
  type ComputedRef,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import type { InventoryScope } from "./inventory-scope.types.ts";
import type {
  StockLocationActivity,
  StockLocationType,
  StockLocationsPageParams,
  StockLocationsListParams,
} from "./stock-location.types.ts";
import { STOCK_LOCATION_SEARCH_DELAY } from "./stock-location.constants.ts";
import {
  parseStockLocationsParams,
  stockLocationsListParams,
  stockLocationsUrlParams,
} from "./stock-locations-page-state.ts";
export interface StockLocationsPageState {
  params: ComputedRef<StockLocationsPageParams>;
  listParams: ComputedRef<StockLocationsListParams>;
  searchText: Ref<string>;
  setSearch(value: string): void;
  submitSearch(): void;
  clearSearch(): void;
  setActivity(value: StockLocationActivity): void;
  setType(value: StockLocationType | null): void;
  setParent(value: string | null): void;
  showChildren(id: string): void;
  clearFilters(): void;
  searchAll(value: string): void;
  setPagination(value: { page: number; limit: number }): void;
  firstPage(): void;
}
export function useStockLocationsPageState(
  scope: Ref<InventoryScope>,
  warehouseId: Ref<string>,
): StockLocationsPageState {
  const route = useRoute(),
    router = useRouter();
  const params = computed(() => parseStockLocationsParams(route.query)),
    searchText = ref(params.value.search);
  let timer: ReturnType<typeof setTimeout> | undefined;
  function cancel(): void {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }
  function navigate(next: StockLocationsPageParams, replace = true): void {
    const target = {
      query: { ...route.query, ...stockLocationsUrlParams(next) },
      hash: route.hash,
    };
    void (replace ? router.replace(target) : router.push(target));
  }
  function submitSearch(): void {
    cancel();
    navigate({ ...params.value, search: searchText.value.trim(), page: 1 });
  }
  function clearFilters(): void {
    cancel();
    searchText.value = "";
    navigate({
      ...params.value,
      search: "",
      activity: "all",
      locationType: null,
      parentLocationId: null,
      page: 1,
    });
  }
  function filter(changes: Partial<StockLocationsPageParams>): void {
    cancel();
    navigate({
      ...params.value,
      search: searchText.value.trim(),
      ...changes,
      page: 1,
    });
  }
  watch(
    () => route.fullPath,
    () => {
      cancel();
      searchText.value = params.value.search;
      const normalized = stockLocationsUrlParams(params.value);
      if (
        Object.entries(normalized).some(
          ([key, value]) => route.query[key] !== value,
        )
      )
        navigate(params.value);
    },
    { immediate: true },
  );
  watch(
    scope,
    (current, previous) => {
      if (
        previous[0] &&
        previous[1] &&
        current.some((value, index) => value !== previous[index])
      )
        clearFilters();
    },
    { flush: "sync" },
  );
  watch(warehouseId, clearFilters, { flush: "sync" });
  onScopeDispose(cancel);
  return {
    params,
    listParams: computed(() => stockLocationsListParams(params.value)),
    searchText,
    setSearch: (value) => {
      searchText.value = value;
      cancel();
      timer = setTimeout(submitSearch, STOCK_LOCATION_SEARCH_DELAY);
    },
    submitSearch,
    clearSearch: () => {
      searchText.value = "";
      submitSearch();
    },
    setActivity: (value) => filter({ activity: value }),
    setType: (value) => filter({ locationType: value }),
    setParent: (value) => filter({ parentLocationId: value }),
    clearFilters,
    showChildren: (id) => {
      cancel();
      searchText.value = "";
      navigate({
        ...params.value,
        search: "",
        activity: "all",
        locationType: null,
        parentLocationId: id,
        page: 1,
      });
    },
    searchAll: (value) => {
      cancel();
      searchText.value = value;
      navigate({
        ...params.value,
        search: value.trim(),
        activity: "all",
        locationType: null,
        parentLocationId: null,
        page: 1,
      });
    },
    setPagination: (value) => {
      cancel();
      const next = parseStockLocationsParams({
        ...stockLocationsUrlParams(params.value),
        search: searchText.value,
        page: String(value.page),
        limit: String(value.limit),
      });
      if (
        next.limit !== params.value.limit ||
        next.search !== params.value.search
      )
        next.page = 1;
      navigate(next, false);
    },
    firstPage: () => navigate({ ...params.value, page: 1 }),
  };
}
