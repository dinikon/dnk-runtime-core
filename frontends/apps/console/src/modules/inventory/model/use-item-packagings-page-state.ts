import {
  computed,
  onScopeDispose,
  ref,
  watch,
  type ComputedRef,
  type Ref,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { ITEM_PACKAGING_SEARCH_DELAY } from "./item-packaging.constants.ts";
import {
  itemPackagingsListParams,
  itemPackagingsUrlParams,
  parseItemPackagingsParams,
} from "./item-packagings-page-state.ts";
import type {
  ItemPackagingsListParams,
  ItemPackagingsPageParams,
} from "./item-packaging.types.ts";
import type { InventoryScope } from "./inventory-scope.types.ts";

interface ItemPackagingsPageState {
  params: ComputedRef<ItemPackagingsPageParams>;
  listParams: ComputedRef<ItemPackagingsListParams>;
  searchText: Ref<string>;
  setSearch(value: string): void;
  submitSearch(): void;
  clearSearch(): void;
  clearFilters(): void;
  searchAll(value: string): void;
  setPagination(value: { page: number; limit: number }): void;
  firstPage(): void;
}

export function useItemPackagingsPageState(
  scope: Ref<InventoryScope>,
  itemId: Ref<string>,
): ItemPackagingsPageState {
  const route = useRoute(),
    router = useRouter();
  const params = computed(() => parseItemPackagingsParams(route.query));
  const searchText = ref(params.value.search);
  let timer: ReturnType<typeof setTimeout> | undefined;
  function cancelSearch(): void {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }
  function navigate(next: ItemPackagingsPageParams, replace = true): void {
    const target = {
      query: { ...route.query, ...itemPackagingsUrlParams(next) },
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
    timer = setTimeout(submitSearch, ITEM_PACKAGING_SEARCH_DELAY);
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
      const normalized = itemPackagingsUrlParams(params.value);
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
  watch(itemId, () => { cancelSearch(); searchText.value=""; navigate({...params.value,search:"",page:1}); }, {flush:"sync"});
  onScopeDispose(cancelSearch);
  return {
    params,
    listParams: computed(() => itemPackagingsListParams(params.value)),
    searchText,
    setSearch,
    submitSearch,
    clearSearch,
    clearFilters: () => {
      cancelSearch();
      searchText.value = "";
      navigate({ ...params.value, search: "", page: 1 });
    },
    searchAll: (value) => {
      cancelSearch();
      searchText.value = value;
      navigate({
        ...params.value,
        search: value.trim(),
        page: 1,
      });
    },
    setPagination: (value) => {
      cancelSearch();
      const next = parseItemPackagingsParams({
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
