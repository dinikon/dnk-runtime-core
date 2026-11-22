import type {
  CalculationMetadata,
  CatalogPricePage,
} from "./feed-calculation.types";
import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import {
  searchCatalogPreviewProducts,
  searchCatalogPreviewVariants,
} from "@/modules/catalog";
import { feedCalculationApi } from "../api/feed-calculation.api";
import { useFeedScope } from "./use-feed-scope";
import { calculationKeys } from "./feed-calculation.query-keys";
export function useCalculationMetadata(
  enabled?: Ref<boolean>,
): UseQueryReturnType<CalculationMetadata, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => calculationKeys.metadata(scope.value)),
    queryFn: ({ signal }) => feedCalculationApi.metadata(signal),
    enabled: computed(
      () => !!scope.value[0] && !!scope.value[1] && (enabled?.value ?? true),
    ),
    staleTime: 300000,
    retry: false,
  });
}
export function useCalculationProducts(
  locale: Ref<string>,
  search: Ref<string>,
  offset: Ref<number>,
  enabled: Ref<boolean>,
): UseQueryReturnType<CatalogPricePage, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() =>
      calculationKeys.products(
        scope.value,
        locale.value,
        search.value,
        offset.value,
      ),
    ),
    queryFn: ({ signal }) =>
      searchCatalogPreviewProducts(
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
export function useCalculationVariants(
  rootId: Ref<string | undefined>,
  locale: Ref<string>,
  offset: Ref<number>,
): UseQueryReturnType<CatalogPricePage, Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() =>
      calculationKeys.variants(
        scope.value,
        rootId.value,
        locale.value,
        offset.value,
      ),
    ),
    queryFn: ({ signal }) =>
      searchCatalogPreviewVariants(
        rootId.value!,
        locale.value,
        offset.value,
        signal,
      ),
    enabled: computed(
      () => !!scope.value[0] && !!scope.value[1] && !!rootId.value,
    ),
    retry: false,
  });
}
