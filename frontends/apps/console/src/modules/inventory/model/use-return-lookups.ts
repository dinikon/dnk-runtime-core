import {
  computed,
  ref,
  watch,
  onScopeDispose,
  type Ref,
  type ComputedRef,
} from "vue";
import {
  useCounterpartyReferencesQuery,
  type CounterpartyReferencesParams,
} from "@/modules/crm";
import { useWarehousesQuery } from "./use-warehouses-query";
import type { WarehousesListParams } from "./warehouse.types";
import type { ReturnReferenceOption } from "./return.types";
import type { InventoryScopeState } from "./use-inventory-scope";
export interface ReturnLookup {
  search: Ref<string>;
  offset: Ref<number>;
  items: ComputedRef<ReturnReferenceOption[]>;
  total: ComputedRef<number>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  setSearch(v: string): void;
  page(offset: number): void;
  retry(): void;
}
export function useReturnLookups(
  scope: InventoryScopeState,
  activeWarehouses: boolean,
): { warehouses: ReturnLookup; owners: ReturnLookup } {
  const warehouseSearch = ref(""),
    ownerSearch = ref(""),
    warehouseCommitted = ref(""),
    ownerCommitted = ref(""),
    warehouseOffset = ref(0),
    ownerOffset = ref(0);
  let warehouseTimer: ReturnType<typeof setTimeout> | undefined,
    ownerTimer: ReturnType<typeof setTimeout> | undefined;
  const wp = computed<WarehousesListParams>(() => ({
      search: warehouseCommitted.value,
      isActive: activeWarehouses ? true : null,
      offset: warehouseOffset.value,
      limit: 20,
    })),
    op = computed<CounterpartyReferencesParams>(() => ({
      model_key: "crm.company",
      search: ownerCommitted.value,
      offset: ownerOffset.value,
      limit: 20,
    }));
  const warehouses = useWarehousesQuery(wp, scope),
    owners = useCounterpartyReferencesQuery(op, scope.key, scope.ready);
  function reset(): void {
    clearTimeout(warehouseTimer);
    clearTimeout(ownerTimer);
    warehouseSearch.value = "";
    ownerSearch.value = "";
    warehouseCommitted.value = "";
    ownerCommitted.value = "";
    warehouseOffset.value = 0;
    ownerOffset.value = 0;
  }
  watch(scope.key, reset, { flush: "sync" });
  onScopeDispose(() => {
    clearTimeout(warehouseTimer);
    clearTimeout(ownerTimer);
  });
  return {
    warehouses: {
      search: warehouseSearch,
      offset: warehouseOffset,
      items: computed(
        () =>
          warehouses.data.value?.items.map((w) => ({
            id: w.id,
            name: `${w.code} — ${w.name}`,
          })) ?? [],
      ),
      total: computed(() => warehouses.data.value?.total ?? 0),
      loading: computed(
        () =>
          warehouses.isFetching.value ||
          warehouseSearch.value.trim() !== warehouseCommitted.value,
      ),
      error: computed(() => warehouses.error.value?.message ?? ""),
      setSearch: (v) => {
        warehouseSearch.value = v;
        clearTimeout(warehouseTimer);
        warehouseTimer = setTimeout(() => {
          warehouseCommitted.value = v.trim();
          warehouseOffset.value = 0;
        }, 250);
      },
      page: (v) => (warehouseOffset.value = v),
      retry: () => {
        void warehouses.refetch();
      },
    },
    owners: {
      search: ownerSearch,
      offset: ownerOffset,
      items: computed(
        () =>
          owners.data.value?.items.map((o) => ({ id: o.id, name: o.name })) ??
          [],
      ),
      total: computed(() => owners.data.value?.total ?? 0),
      loading: computed(
        () =>
          owners.isFetching.value ||
          ownerSearch.value.trim() !== ownerCommitted.value,
      ),
      error: computed(() => owners.error.value?.message ?? ""),
      setSearch: (v) => {
        ownerSearch.value = v;
        clearTimeout(ownerTimer);
        ownerTimer = setTimeout(() => {
          ownerCommitted.value = v.trim();
          ownerOffset.value = 0;
        }, 250);
      },
      page: (v) => (ownerOffset.value = v),
      retry: () => {
        void owners.refetch();
      },
    },
  };
}
