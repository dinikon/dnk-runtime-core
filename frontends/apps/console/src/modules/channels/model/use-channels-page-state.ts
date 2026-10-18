import { type ComputedRef, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { parsePage, parseStockStatus } from "./channels.url-state";
import type { ChannelsFilters, PublicationsFilters } from "./channels.types";
interface ChannelsPageState {
  page: ComputedRef<number>;
  tab: ComputedRef<string>;
  search: ComputedRef<string>;
  stockStatus: ComputedRef<string>;
  listFilters: ComputedRef<ChannelsFilters>;
  publicationFilters: ComputedRef<PublicationsFilters>;
  setPage: (value: number) => void;
  setTab: (value: string) => void;
  setFilters: (value: { search: string; stockStatus: string }) => void;
}
export function useChannelsPageState(): ChannelsPageState {
  const route = useRoute(),
    router = useRouter();
  const page = computed(() => parsePage(route.query.page));
  const tab = computed(() =>
    route.query.tab === "connection" ? "connection" : "publications",
  );
  const search = computed(() =>
    typeof route.query.search === "string"
      ? route.query.search.slice(0, 200)
      : "",
  );
  const stockStatus = computed(() => parseStockStatus(route.query.stock));
  const listFilters = computed(() => ({
    offset: (page.value - 1) * 20,
    limit: 20,
  }));
  const publicationFilters = computed(() => ({
    ...listFilters.value,
    search: search.value,
    stockStatus: stockStatus.value,
  }));
  function setPage(value: number): void {
    void router.replace({
      query: { ...route.query, page: value > 1 ? String(value) : undefined },
    });
  }
  function setTab(value: string): void {
    void router.replace({
      query: {
        ...route.query,
        tab: value === "connection" ? value : undefined,
      },
    });
  }
  function setFilters(value: { search: string; stockStatus: string }): void {
    void router.replace({
      query: {
        ...route.query,
        search: value.search || undefined,
        stock: value.stockStatus || undefined,
        page: undefined,
      },
    });
  }
  return {
    page,
    tab,
    search,
    stockStatus,
    listFilters,
    publicationFilters,
    setPage,
    setTab,
    setFilters,
  };
}
