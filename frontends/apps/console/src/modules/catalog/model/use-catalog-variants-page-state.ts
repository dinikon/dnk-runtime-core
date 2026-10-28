import { computed, watch, type Ref, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { VariantPagination } from "./use-catalog-variants";
interface VariantsPageState {
  pagination: ComputedRef<VariantPagination>;
  selected: ComputedRef<string>;
  open(id: string): void;
  close(): void;
  setPage(value: { page: number; limit: number }): void;
}
export function useCatalogVariantsPageState(
  rootId: Ref<string>,
  locale: Ref<string>,
): VariantsPageState {
  const route = useRoute(),
    router = useRouter();
  const selected = computed(() =>
    typeof route.query.variant === "string" ? route.query.variant : "",
  );
  const pagination = computed(() => {
    const requested = Number(route.query.variants_limit),
      limit = [25, 50, 100].includes(requested) ? requested : 25;
    const requestedOffset = Number(route.query.variants_offset ?? 0);
    const offset = Number.isFinite(requestedOffset)
      ? Math.floor(Math.max(0, Math.min(2147483600, requestedOffset)) / limit) *
        limit
      : 0;
    return { offset, limit };
  });
  function open(id: string): void {
    void router.replace({ query: { ...route.query, variant: id } });
  }
  function close(): void {
    void router.replace({ query: { ...route.query, variant: undefined } });
  }
  function setPage(value: { page: number; limit: number }): void {
    const limit = [25, 50, 100].includes(value.limit) ? value.limit : 25;
    const offset = Math.max(0, (value.page - 1) * limit);
    void router.replace({
      query: {
        ...route.query,
        variants_limit: limit === 25 ? undefined : String(limit),
        variants_offset: offset ? String(offset) : undefined,
      },
    });
  }
  watch(locale, () => {
    if (route.query.variants_offset)
      void router.replace({
        query: { ...route.query, variants_offset: undefined },
      });
  });
  watch(rootId, () => {
    void router.replace({
      query: { ...route.query, variant: undefined, variants_offset: undefined },
    });
  });
  return { pagination, selected, open, close, setPage };
}
