import type { PackagingTypeActivity } from "./packaging-type.types.ts";
import {
  computed,
  onScopeDispose,
  ref,
  watch,
  type ComputedRef,
  type Ref,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import { PACKAGING_TYPE_SEARCH_DELAY } from "./packaging-type.constants.ts";
import {
  packagingTypesListParams,
  packagingTypesUrlParams,
  parsePackagingTypesParams,
} from "./packaging-types-page-state.ts";
import type {
  PackagingTypesListParams,
  PackagingTypesPageParams,
} from "./packaging-type.types.ts";
import type { InventoryScope } from "./inventory-scope.types.ts";

interface PackagingTypesPageState {
  params: ComputedRef<PackagingTypesPageParams>;
  listParams: ComputedRef<PackagingTypesListParams>;
  searchText: Ref<string>;
  setSearch(value: string): void;
  submitSearch(): void;
  clearSearch(): void;
  setActivity(value: PackagingTypeActivity): void;
  clearFilters(): void;
  searchAll(value: string): void;
  setPagination(value: { page: number; limit: number }): void;
  firstPage(): void;
}

export function usePackagingTypesPageState(
  scope: Ref<InventoryScope>,
): PackagingTypesPageState {
  const route = useRoute(),
    router = useRouter();
  const params = computed(() => parsePackagingTypesParams(route.query));
  const searchText = ref(params.value.search);
  let timer: ReturnType<typeof setTimeout> | undefined;
  function cancelSearch(): void {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }
  function navigate(next: PackagingTypesPageParams, replace = true): void {
    const target = {
      query: { ...route.query, ...packagingTypesUrlParams(next) },
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
    timer = setTimeout(submitSearch, PACKAGING_TYPE_SEARCH_DELAY);
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
      const normalized = packagingTypesUrlParams(params.value);
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
      navigate({ ...params.value, search: "", activity: "all", page: 1 });
    },
    { flush: "sync" },
  );
  onScopeDispose(cancelSearch);
  return {
    params,
    listParams: computed(() => packagingTypesListParams(params.value)),
    searchText,
    setSearch,
    submitSearch,
    clearSearch,
    setActivity: (activity) => {
      cancelSearch();
      navigate({
        ...params.value,
        search: searchText.value.trim(),
        activity,
        page: 1,
      });
    },
    clearFilters: () => {
      cancelSearch();
      searchText.value = "";
      navigate({ ...params.value, search: "", activity: "all", page: 1 });
    },
    searchAll: (value) => {
      cancelSearch();
      searchText.value = value;
      navigate({
        ...params.value,
        search: value.trim(),
        activity: "all",
        page: 1,
      });
    },
    setPagination: (value) => {
      cancelSearch();
      const next = parsePackagingTypesParams({
        is_active:
          params.value.activity === "all"
            ? undefined
            : String(params.value.activity === "active"),
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
