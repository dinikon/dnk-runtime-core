import {
  useMutation,
  useQueryClient,
  type UseMutationReturnType,
} from "@tanstack/vue-query";
import { computed, type Ref } from "vue";
import { useScopedQueryCache } from "@/shared/model/use-scoped-query-cache";
import { catalogApi } from "../api/catalog.api";
import type {
  CatalogSkuSelection,
  SetCatalogSkuResult,
} from "./catalog-sku.types";

export interface SetCatalogSkuInput {
  id: string;
  variantId?: string;
  tenant: string;
  session: string;
  selection: CatalogSkuSelection;
}

export function useSetCatalogSku(
  tenant: Ref<string>,
  session: Ref<string>,
  invalidateInventory: () => Promise<void>,
): UseMutationReturnType<
  SetCatalogSkuResult,
  Error,
  SetCatalogSkuInput,
  unknown
> {
  const cache = useQueryClient();
  useScopedQueryCache(
    computed(() => [tenant.value, session.value] as const),
    "catalog",
  );
  return useMutation({
    mutationKey: computed(() => [
      "catalog",
      tenant.value,
      session.value,
      "set-sku",
    ]),
    retry: false,
    mutationFn: (value: SetCatalogSkuInput) =>
      catalogApi.setSku(value.id, value.selection, value.variantId),
    onSuccess: async (_result, value) => {
      if (value.session !== session.value) return;
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["catalog", value.tenant] }),
        invalidateInventory(),
      ]);
    },
  });
}
