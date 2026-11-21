import {
  computed,
  ref,
  watch,
  onScopeDispose,
  type Ref,
  type ComputedRef,
} from "vue";
import { useQuery } from "@tanstack/vue-query";
import { useCounterpartyReferencesQuery } from "@/modules/crm";
import { listWarehouses } from "../api/warehouse.api";
import { listStockLocations } from "../api/stock-location.api";
import { listInventoryItems } from "../api/inventory-item.api";
import { listStockLots } from "../api/stock-lot.api";
import { listStockSerials } from "../api/stock-serial.api";
import type { InventoryScopeState } from "./use-inventory-scope";
import type {
  StockFilters,
  StockFilterKind,
  StockFilterOptionsPage,
} from "./stock-accounting.types";
export interface StockAccountingPicker {
  kind: Ref<StockFilterKind | null>;
  search: Ref<string>;
  offset: Ref<number>;
  page: ComputedRef<StockFilterOptionsPage>;
  loading: ComputedRef<boolean>;
  error: ComputedRef<string>;
  setSearch(value: string): void;
  open(value: StockFilterKind): void;
  close(): void;
  retry(): void;
}
export function useStockAccountingPicker(
  filters: Ref<StockFilters>,
  scope: InventoryScopeState,
): StockAccountingPicker {
  const kind = ref<StockFilterKind | null>(null),
    search = ref(""),
    committed = ref(""),
    offset = ref(0);
  let timer: ReturnType<typeof setTimeout> | undefined;
  function close(): void {
    clearTimeout(timer);
    kind.value = null;
    search.value = "";
    committed.value = "";
    offset.value = 0;
  }
  watch(scope.key, close, { flush: "sync" });
  onScopeDispose(() => clearTimeout(timer));
  const input = computed(() => ({
    kind: kind.value,
    search: committed.value,
    offset: offset.value,
    warehouseId: filters.value.warehouseId ?? "",
    itemId: filters.value.inventoryItemId ?? "",
  }));
  const options = useQuery({
    queryKey: computed(
      () =>
        [
          "inventory",
          ...scope.key.value,
          "accounting-picker",
          { ...input.value },
        ] as const,
    ),
    enabled: computed(
      () => scope.ready.value && !!kind.value && kind.value !== "ownerId",
    ),
    queryFn: async ({ queryKey, signal }): Promise<StockFilterOptionsPage> => {
      const value = queryKey[5],
        params = { search: value.search, offset: value.offset, limit: 20 };
      switch (value.kind) {
        case "warehouseId": {
          const result = await listWarehouses(
            { ...params, isActive: null },
            signal,
          );
          return {
            items: result.items.map((w) => ({
              id: w.id,
              label: `${w.code} — ${w.name}${w.isActive ? "" : " (неактивен)"}`,
            })),
            total: result.total,
          };
        }
        case "locationId": {
          const result = await listStockLocations(
            value.warehouseId,
            {
              ...params,
              isActive: null,
              locationType: null,
              parentLocationId: null,
            },
            signal,
          );
          return {
            items: result.items.map((l) => ({
              id: l.id,
              label: `${l.code} — ${l.name}${l.isActive ? "" : " (неактивна)"}`,
            })),
            total: result.total,
          };
        }
        case "inventoryItemId": {
          const result = await listInventoryItems(params, signal);
          return {
            items: result.items.map((i) => ({ id: i.id, label: i.sku })),
            total: result.total,
          };
        }
        case "lotId": {
          const result = await listStockLots(value.itemId, params, signal);
          return {
            items: result.items.map((i) => ({ id: i.id, label: i.number })),
            total: result.total,
          };
        }
        case "serialId": {
          const result = await listStockSerials(value.itemId, params, signal);
          return {
            items: result.items.map((i) => ({ id: i.id, label: i.number })),
            total: result.total,
          };
        }
        default:
          return { items: [], total: 0 };
      }
    },
    staleTime: 0,
    retry: false,
  });
  const ownerParams = computed(() => ({
    model_key: "crm.company" as const,
    search: committed.value,
    offset: offset.value,
    limit: 20,
  }));
  const owners = useCounterpartyReferencesQuery(
    ownerParams,
    scope.key,
    computed(() => scope.ready.value && kind.value === "ownerId"),
  );
  const page = computed<StockFilterOptionsPage>(() =>
    kind.value === "ownerId"
      ? {
          items:
            owners.data.value?.items.map((i) => ({
              id: i.id,
              label: i.name,
            })) ?? [],
          total: owners.data.value?.total ?? 0,
        }
      : (options.data.value ?? { items: [], total: 0 }),
  );
  const loading = computed(
    () =>
      (kind.value === "ownerId"
        ? owners.isFetching.value
        : options.isFetching.value) || search.value.trim() !== committed.value,
  );
  const error = computed(
    () =>
      (kind.value === "ownerId" ? owners.error.value : options.error.value)
        ?.message ?? "",
  );
  function setSearch(value: string): void {
    search.value = value;
    clearTimeout(timer);
    timer = setTimeout(() => {
      committed.value = value.trim();
      offset.value = 0;
    }, 250);
  }
  function open(value: StockFilterKind): void {
    close();
    kind.value = value;
  }
  function retry(): void {
    void (kind.value === "ownerId" ? owners.refetch() : options.refetch());
  }
  return {
    kind,
    search,
    offset,
    page,
    loading,
    error,
    setSearch,
    open,
    close,
    retry,
  };
}
