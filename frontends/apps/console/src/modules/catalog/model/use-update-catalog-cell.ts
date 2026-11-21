import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import type { Ref } from "vue";
import { catalogApi } from "../api/catalog.api";
import type { ProductPatch } from "./product.types";
import { catalogListKeys } from "./catalog-list.query-keys";

export interface UpdateCatalogCell {
  id: string;
  rootId: string | null;
  locale: string;
  tenant: string;
  session: string;
  patch: ProductPatch;
}
export function useUpdateCatalogCell(
  session: Ref<string>,
): UseMutationReturnType<{ id: string }, Error, UpdateCatalogCell, unknown> {
  const cache = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: (value: UpdateCatalogCell) =>
      value.rootId
        ? catalogApi.updateVariant(
            value.rootId,
            value.id,
            value.patch,
            value.locale,
          )
        : catalogApi.updateItem(value.id, value.patch, value.locale),
    onSuccess: async (_result, value) => {
      if (session.value !== value.session) return;
      await cache.invalidateQueries({
        queryKey: catalogListKeys.all(value.tenant, value.session),
      });
    },
  });
}
