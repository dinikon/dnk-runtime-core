import { computed, type Ref } from "vue";
import { useQuery, type UseQueryReturnType } from "@tanstack/vue-query";
import { catalogApi } from "../api/catalog.api";
import { catalogListKeys } from "./catalog-list.query-keys";
import type {
  CatalogQuickEditSelection,
  CatalogQuickEditTarget,
} from "./catalog-table.types";

/** Перед редактированием получает полную спецификацию, сохраняя акции и политику предзаказа. */
export function useCatalogQuickEditQuery(
  selection: Ref<CatalogQuickEditSelection | null>,
  tenant: Ref<string>,
  session: Ref<string>,
  locale: Ref<string>,
): UseQueryReturnType<CatalogQuickEditTarget, Error> {
  return useQuery({
    queryKey: computed(() =>
      catalogListKeys.quickEdit(
        tenant.value,
        session.value,
        locale.value,
        selection.value?.id ?? "",
        selection.value?.rootId ?? null,
        selection.value?.section ?? "",
      ),
    ),
    enabled: computed(
      () => !!selection.value && !!tenant.value && !!locale.value,
    ),
    refetchOnWindowFocus: false,
    queryFn: async ({ signal }) => {
      const target = selection.value!,
        language = locale.value;
      const item = target.rootId
        ? await catalogApi.getVariant(
            target.rootId,
            target.id,
            language,
            signal,
          )
        : await catalogApi.getItem(target.id, language, signal);
      if (
        target.section === "stock" &&
        item.stock_source === "parent" &&
        target.rootId
      ) {
        return {
          item: await catalogApi.getItem(target.rootId, language, signal),
          rootId: null,
          shared: true,
        };
      }
      return { item, rootId: target.rootId, shared: false };
    },
  });
}
