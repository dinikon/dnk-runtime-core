import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { listCategories, type CatalogCategory } from "@/modules/catalog";
import { feedSchemaKeys } from "./feed-schema.query-keys";
import { useFeedScope } from "./use-feed-scope";

export function useFeedCategoryTree(locale: Ref<string | undefined>): UseQueryReturnType<CatalogCategory[], Error> {
  const scope = useFeedScope();
  return useQuery({
    queryKey: computed(() => feedSchemaKeys.catalogCategories(scope.value, locale.value)),
    queryFn: ({ signal }) => listCategories(locale.value!, signal),
    enabled: computed(() => !!scope.value[0] && !!scope.value[1] && !!locale.value),
    retry: false,
  });
}
