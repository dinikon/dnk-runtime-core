import {
  computed,
  onScopeDispose,
  ref,
  watch,
  type ComputedRef,
  type Ref,
} from "vue";
import { useQueryClient } from "@tanstack/vue-query";
import { useInventoryScope } from "./use-inventory-scope";
import { useInventoryItemsQuery } from "./use-inventory-items-query";
import { inventoryItemKeys } from "./inventory-item.query-keys";
import { INVENTORY_SEARCH_DELAY } from "./inventory-item.constants";
import type { InventorySkuOption } from "./inventory-sku.types";

export interface InventorySkuSearch {
  search: Ref<string>;
  options: ComputedRef<readonly InventorySkuOption[]>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  total: ComputedRef<number>;
  reset(): void;
  retry(): void;
  invalidate(): Promise<void>;
}

export function useInventorySkuSearch(
  enabled: Ref<boolean>,
  resetKey?: Ref<string>,
): InventorySkuSearch {
  const scope = useInventoryScope();
  const cache = useQueryClient();
  const search = ref(""),
    committed = ref("");
  let timer: ReturnType<typeof setTimeout> | undefined;
  function cancel(): void {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  }
  function reset(): void {
    cancel();
    search.value = "";
    committed.value = "";
  }
  watch(
    search,
    (value) => {
      cancel();
      timer = setTimeout(() => {
        committed.value = value.trim();
      }, INVENTORY_SEARCH_DELAY);
    },
    { flush: "sync" },
  );
  watch(scope.key, reset, { flush: "sync" });
  if (resetKey) watch(resetKey, reset, { flush: "sync" });
  onScopeDispose(cancel);
  const query = useInventoryItemsQuery(
    computed(() => ({ search: committed.value, offset: 0, limit: 50 })),
    {
      ...scope,
      ready: computed(() => scope.ready.value && enabled.value),
    },
  );
  const loading = computed(
    () =>
      search.value.trim() !== committed.value ||
      query.isFetching.value ||
      (enabled.value && query.isPending.value && !scope.error.value),
  );
  return {
    search,
    options: computed(() =>
      loading.value ? [] : (query.data.value?.items ?? []),
    ),
    loading,
    error: computed(
      () => scope.error.value || query.error.value?.message || "",
    ),
    total: computed(() => query.data.value?.total ?? 0),
    reset,
    retry: () => {
      if (scope.ready.value && enabled.value) void query.refetch();
    },
    invalidate: () =>
      cache.invalidateQueries({
        queryKey: inventoryItemKeys.root(scope.key.value),
      }),
  };
}
