import {
  computed,
  ref,
  watch,
  onBeforeUnmount,
  type Ref,
  type ComputedRef,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import type { SourcesParams, SupplierScope } from "./supplier-source.types";
import { sourcesParams, sourcesQuery } from "./sources-page-state";
export interface SourcesPageState {
  params: ComputedRef<SourcesParams>;
  searchText: Ref<string>;
  change(value: Partial<SourcesParams>): void;
  search(value: string): void;
  clear(): void;
}
export function useSourcesPageState(
  scope: Ref<SupplierScope>,
): SourcesPageState {
  const route = useRoute(),
    router = useRouter();
  const params = computed(() => sourcesParams(route.query)),
    searchText = ref(params.value.search);
  let timer: ReturnType<typeof setTimeout> | undefined;
  function change(value: Partial<SourcesParams>): void {
    void router.replace({
      query: sourcesQuery({ ...params.value, page: 1, ...value }),
    });
  }
  watch(
    () => params.value.search,
    (value) => {
      searchText.value = value;
    },
  );
  watch(
    scope,
    () => {
      clearTimeout(timer);
      searchText.value = params.value.search;
    },
    { flush: "sync" },
  );
  function search(value: string): void {
    searchText.value = value;
    clearTimeout(timer);
    timer = setTimeout(() => change({ search: value.trim() }), 300);
  }
  onBeforeUnmount(() => clearTimeout(timer));
  return {
    params,
    searchText,
    change,
    search,
    clear: () => {
      clearTimeout(timer);
      searchText.value = "";
      void router.replace({ query: {} });
    },
  };
}
