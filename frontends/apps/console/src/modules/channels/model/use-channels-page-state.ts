import { parseIdentityStatus } from "./publication-identity.presentation";
import { type ComputedRef, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { parsePage, parseStockStatus } from "./channels.url-state";
import type { ChannelsFilters, PublicationsFilters } from "./channels.types";
interface ChannelsPageState {
  page: ComputedRef<number>;
  tab: ComputedRef<string>;
  search: ComputedRef<string>;
  stockStatus: ComputedRef<string>;
  bindingStatus: ComputedRef<string>;
  identityStatus: ComputedRef<string>;
  identityKey: ComputedRef<string>;
  exportStatus: ComputedRef<string>;
  setIdentity: (status: string, key?: string) => void;
  listFilters: ComputedRef<ChannelsFilters>;
  publicationFilters: ComputedRef<PublicationsFilters>;
  setPage: (value: number) => void;
  setTab: (value: string) => void;
  setFilters: (value: {
    search: string;
    stockStatus: string;
    bindingStatus?: string;
    identityStatus?: string;
    exportStatus?: string;
  }) => void;
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
  const bindingStatus = computed(() =>
    route.query.binding === "bound" || route.query.binding === "unbound"
      ? route.query.binding
      : "",
  );
  const identityStatus = computed(() =>
    parseIdentityStatus(route.query.identity),
  );
  const identityKey = computed(() =>
    typeof route.query.identityKey === "string"
      ? route.query.identityKey.slice(0, 512)
      : "",
  );
  const exportStatus = computed(() =>
    route.query.export === "enabled" || route.query.export === "disabled"
      ? route.query.export
      : "",
  );
  const listFilters = computed(() => ({
    offset: (page.value - 1) * 20,
    limit: 20,
  }));
  const publicationFilters = computed(() => ({
    ...listFilters.value,
    search: search.value,
    stockStatus: stockStatus.value,
    bindingStatus: bindingStatus.value,
    identityStatus: identityStatus.value,
    identityKey: identityKey.value,
    exportStatus: exportStatus.value,
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
  function setFilters(value: {
    search: string;
    stockStatus: string;
    bindingStatus?: string;
    identityStatus?: string;
    exportStatus?: string;
  }): void {
    void router.replace({
      query: {
        ...route.query,
        search: value.search || undefined,
        stock: value.stockStatus || undefined,
        binding: value.bindingStatus || undefined,
        identity: value.identityStatus || undefined,
        export: value.exportStatus || undefined,
        identityKey:
          value.identityStatus === identityStatus.value
            ? identityKey.value || undefined
            : undefined,
        page: undefined,
      },
    });
  }
  function setIdentity(status: string, key?: string): void {
    void router.replace({
      query: {
        ...route.query,
        identity: status || undefined,
        identityKey: key || undefined,
        search: undefined,
        stock: undefined,
        binding: undefined,
        page: undefined,
      },
    });
  }
  return {
    page,
    tab,
    search,
    stockStatus,
    bindingStatus,
    identityStatus,
    identityKey,
    exportStatus,
    setIdentity,
    listFilters,
    publicationFilters,
    setPage,
    setTab,
    setFilters,
  };
}
