import {
  computed,
  onScopeDispose,
  ref,
  watch,
  type ComputedRef,
  type Ref,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { INVENTORY_SEARCH_DELAY } from "./inventory-item.constants.ts";
import {
  inventoryItemsListParams,
  inventoryItemsUrlParams,
  parseInventoryItemsParams,
} from "./inventory-items-page-state.ts";
import type {
  InventoryItemsListParams,
  InventoryItemsPageParams,
} from "./inventory-item.types.ts";
import type { InventoryScope } from "./inventory-scope.types.ts";

interface InventoryItemsPageState {
  params: ComputedRef<InventoryItemsPageParams>;
  listParams: ComputedRef<InventoryItemsListParams>;
  searchText: Ref<string>;
  setSearch(value: string): void;
  submitSearch(): void;
  clearSearch(): void;
  setPagination(value: { page: number; limit: number }): void;
  firstPage(): void;
  cancelSearch(): void;
  reconcilePage(total: number): void;
}

export function useInventoryItemsPageState(
  scope: Ref<InventoryScope>,
): InventoryItemsPageState {
  const route = useRoute(),
    router = useRouter();
  const params = computed(() => parseInventoryItemsParams(route.query));
  const searchText = ref(params.value.search);
  let timer: ReturnType<typeof setTimeout> | undefined;
  function cancelSearch(): void {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }
  function navigate(next: InventoryItemsPageParams, replace = true): void {
    const target = {
      query: { ...route.query, ...inventoryItemsUrlParams(next) },
      hash: route.hash,
    };
    void (replace ? router.replace(target) : router.push(target));
  }
  function submitSearch(): void {
    cancelSearch();
    navigate({ ...params.value, search: searchText.value.trim(), page: 1 });
  }
  function setSearch(value: string): void {
    searchText.value = value;
    cancelSearch();
    timer = setTimeout(submitSearch, INVENTORY_SEARCH_DELAY);
  }
  function clearSearch(): void {
    searchText.value = "";
    submitSearch();
  }
  watch(
    () => route.fullPath,
    () => {
      cancelSearch();
      searchText.value = params.value.search;
      const normalized = inventoryItemsUrlParams(params.value);
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
        !previous[0] ||
        !previous[1] ||
        current.every((value, index) => value === previous[index])
      )
        return;
      cancelSearch();
      searchText.value = "";
      navigate({ ...params.value, search: "", page: 1 });
    },
    { flush: "sync" },
  );
  onScopeDispose(cancelSearch);
  return {
    params,
    listParams: computed(() => inventoryItemsListParams(params.value)),
    searchText,
    setSearch,
    submitSearch,
    clearSearch,
    setPagination: (value) => {
      cancelSearch();
      const next = parseInventoryItemsParams({
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
    cancelSearch,
    reconcilePage: (total) => {
      const page = Math.min(
        params.value.page,
        Math.max(1, Math.ceil(total / params.value.limit)),
      );
      if (page !== params.value.page) navigate({ ...params.value, page });
    },
  };
}
