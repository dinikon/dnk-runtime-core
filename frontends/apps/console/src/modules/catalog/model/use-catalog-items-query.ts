import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { catalogApi } from "../api/catalog.api";
import {
  CATALOG_PAGE_SIZE,
  type CatalogItemsParams,
} from "./catalog-list-state";
import { catalogListKeys } from "./catalog-list.query-keys";
import type { CatalogItemsPage } from "./catalog.types";

export function useCatalogItemsQuery(
  tenant: MaybeRefOrGetter<string>,
  session: MaybeRefOrGetter<string>,
  locale: MaybeRefOrGetter<string>,
  params: MaybeRefOrGetter<CatalogItemsParams>,
): UseQueryReturnType<CatalogItemsPage, Error> {
  return useQuery({
    queryKey: computed(() =>
      catalogListKeys.list(
        toValue(tenant),
        toValue(session),
        toValue(locale),
        toValue(params),
      ),
    ),
    enabled: computed(() => !!toValue(tenant) && !!toValue(locale)),
    queryFn: ({ signal }) => {
      const value = toValue(params);
      return catalogApi.listItems(
        toValue(locale),
        value.search,
        (value.page - 1) * CATALOG_PAGE_SIZE,
        CATALOG_PAGE_SIZE,
        value.status,
        signal,
      );
    },
  });
}
