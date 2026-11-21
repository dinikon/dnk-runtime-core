import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  catalogPage,
  parseCatalogItemsParams,
  type CatalogItemsParams,
} from "./catalog-list-state.ts";
import type { ProductStatus } from "./product.types";

interface CatalogItemsPageState {
  params: ComputedRef<CatalogItemsParams>;
  search: (value: string) => void;
  status: (value: ProductStatus | undefined) => void;
  page: (value: number) => void;
  clear: () => void;
}

export function useCatalogItemsPageState(): CatalogItemsPageState {
  const route = useRoute(),
    router = useRouter();
  const params = computed(() => parseCatalogItemsParams(route.query));
  function replace(values: Record<string, string | number | undefined>): void {
    void router.replace({
      query: { ...route.query, ...values },
      hash: route.hash,
    });
  }
  return {
    params,
    search: (search) =>
      replace({ search: search || undefined, page: undefined }),
    status: (status) => replace({ status, page: undefined }),
    page: (page) =>
      replace({
        page: catalogPage(page) === 1 ? undefined : catalogPage(page),
      }),
    clear: () =>
      replace({ search: undefined, status: undefined, page: undefined }),
  };
}
