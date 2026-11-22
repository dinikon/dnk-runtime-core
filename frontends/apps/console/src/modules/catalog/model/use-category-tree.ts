import { computed } from "vue";
import { useQuery } from "@tanstack/vue-query";
import { listCategories } from "../api/category.api";
import { categoryTree } from "./category-tree";
import type { useCatalogContext } from "./use-catalog-context";

export function useCategoryTree(ctx: ReturnType<typeof useCatalogContext>) {
  const query = useQuery({
    queryKey: computed(() => ctx.key("category-tree")),
    enabled: computed(() => !!ctx.tenantId.value && !!ctx.locale.value),
    queryFn: ({ signal }) => listCategories(ctx.locale.value, signal),
  });
  return {
    query,
    options: computed(() => categoryTree(query.data.value ?? [])),
  };
}
