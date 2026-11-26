import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import {
  listCatalogLocales,
  searchCatalogPublicationProducts,
  searchCatalogPublicationVariants,
} from "@/modules/catalog";
import { useFeedScope } from "./use-feed-scope";
import { publicationKeys } from "./feed-publication.query-keys";
import { feedPublicationApi } from "../api/feed-publication.api";
import type {
  PublicationFilters,
  PublicationPage,
  PublicationCatalogPage,
  Publication,
} from "./feed-publication.types";
export function usePublications(
  id: Ref<string>,
  filters: Ref<PublicationFilters>,
): UseQueryReturnType<PublicationPage, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() =>
      publicationKeys.list(scope.value, id.value, filters.value),
    ),
    queryFn: ({ signal }) =>
      feedPublicationApi.list(id.value, filters.value, signal),
    enabled: computed(() => !!scope.value[0] && !!scope.value[1] && !!id.value),
    retry: false,
  });
}
export function usePublicationProducts(
  locale: Ref<string>,
  search: Ref<string>,
  offset: Ref<number>,
  enabled: Ref<boolean>,
): UseQueryReturnType<PublicationCatalogPage, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() =>
      publicationKeys.products(
        scope.value,
        locale.value,
        search.value,
        offset.value,
      ),
    ),
    queryFn: ({ signal }) =>
      searchCatalogPublicationProducts(
        locale.value,
        search.value,
        offset.value,
        signal,
      ),
    enabled: computed(
      () => !!scope.value[0] && !!scope.value[1] && enabled.value,
    ),
    retry: false,
  });
}
export function usePublicationVariants(
  rootId: Ref<string>,
  locale: Ref<string>,
  offset: Ref<number>,
  enabled: Ref<boolean>,
): UseQueryReturnType<PublicationCatalogPage, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() =>
      publicationKeys.variants(
        scope.value,
        rootId.value,
        locale.value,
        offset.value,
      ),
    ),
    queryFn: ({ signal }) =>
      searchCatalogPublicationVariants(
        rootId.value,
        locale.value,
        offset.value,
        signal,
      ),
    enabled: computed(
      () =>
        !!scope.value[0] && !!scope.value[1] && !!rootId.value && enabled.value,
    ),
    retry: false,
  });
}

export function usePublication(
  id: Ref<string>,
  locale: Ref<string>,
): UseQueryReturnType<Publication, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() =>
      publicationKeys.detail(scope.value, id.value, locale.value),
    ),
    queryFn: ({ signal }) =>
      feedPublicationApi.get(id.value, locale.value, signal),
    enabled: computed(() => !!scope.value[0] && !!scope.value[1] && !!id.value),
    retry: false,
  });
}

export function usePublicationLocales(): UseQueryReturnType<
  { code: string; name: string }[],
  Error
> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => publicationKeys.locales(scope.value)),
    queryFn: ({ signal }) => listCatalogLocales(signal),
    enabled: computed(() => Boolean(scope.value[0] && scope.value[1])),
    retry: false,
  });
}
