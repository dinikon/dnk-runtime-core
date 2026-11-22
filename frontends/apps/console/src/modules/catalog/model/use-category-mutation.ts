import { useMutation, useQueryClient } from "@tanstack/vue-query";
import { changeCategory } from "../api/category.api";
import type { useCatalogContext } from "./use-catalog-context";

export function useCategoryMutation(ctx: ReturnType<typeof useCatalogContext>) {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: changeCategory,
    onMutate: () => ({
      key: [
        "catalog",
        ctx.tenantId.value,
        ctx.sessionKey.value,
        "category-tree",
      ],
    }),
    onSuccess: async (_data, _change, context) => {
      await cache.invalidateQueries({ queryKey: context.key });
    },
  });
}
