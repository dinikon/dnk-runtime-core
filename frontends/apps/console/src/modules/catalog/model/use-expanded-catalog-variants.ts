import { computed, ref, watch, type Ref, type ComputedRef } from "vue";
import { useQueries } from "@tanstack/vue-query";
import { getApiErrorMessage } from "@/app/providers/http";
import { catalogApi } from "../api/catalog.api";
import { catalogListKeys } from "./catalog-list.query-keys";
import type { CatalogVariantExpansions } from "./catalog-table.types";

/** Раскрытые семьи читаются по требованию; пагинация корней остаётся независимой. */
export function useExpandedCatalogVariants(
  tenant: Ref<string>,
  session: Ref<string>,
  locale: Ref<string>,
  scope: Ref<string>,
): {
  expanded: ComputedRef<CatalogVariantExpansions>;
  toggle(id: string): void;
  page(id: string, offset: number): void;
  retry(id: string): void;
} {
  const offsets = ref<Record<string, number>>({});
  watch(
    [session, locale, scope],
    () => {
      offsets.value = {};
    },
    { flush: "sync" },
  );
  const ids = computed(() => Object.keys(offsets.value));
  const queries = useQueries({
    queries: computed(() =>
      ids.value.map((rootId) => {
        const language = locale.value;
        const pagination = { offset: offsets.value[rootId] ?? 0, limit: 25 };
        return {
          queryKey: catalogListKeys.variants(
            tenant.value,
            session.value,
            rootId,
            language,
            pagination,
          ),
          enabled: !!tenant.value && !!language,
          queryFn: ({ signal }: { signal: AbortSignal }) =>
            catalogApi.listVariants(
              rootId,
              language,
              pagination.offset,
              pagination.limit,
              signal,
            ),
        };
      }),
    ),
  });
  const expanded = computed<CatalogVariantExpansions>(() =>
    Object.fromEntries(
      ids.value.map((id, index) => {
        const query = queries.value[index]!;
        return [
          id,
          {
            items: query.data?.items ?? [],
            loading: query.isPending,
            fetching: query.isFetching,
            error: query.error
              ? getApiErrorMessage(
                  query.error,
                  "Не удалось загрузить варианты.",
                )
              : "",
            total: query.data?.total ?? 0,
            offset: offsets.value[id] ?? 0,
            limit: 25,
          },
        ];
      }),
    ),
  );
  function toggle(id: string): void {
    const next = { ...offsets.value };
    if (id in next) delete next[id];
    else next[id] = 0;
    offsets.value = next;
  }
  function page(id: string, offset: number): void {
    if (id in offsets.value)
      offsets.value = { ...offsets.value, [id]: Math.max(0, offset) };
  }
  function retry(id: string): void {
    void queries.value[ids.value.indexOf(id)]?.refetch();
  }
  return { expanded, toggle, page, retry };
}
