import {
  computed,
  ref,
  watch,
  onScopeDispose,
  type Ref,
  type ComputedRef,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import type { StockReadKind, StockFilters } from "./stock-accounting.types";
import {
  readStockAccountingQuery,
  changeStockFilters,
} from "./stock-accounting-state";
import { stockReadLocation } from "./stock-accounting-navigation";
export interface StockAccountingState {
  params: ComputedRef<import("./stock-accounting.types").StockReadParams>;
  error: ComputedRef<string>;
  search: Ref<string>;
  patch(
    value: Partial<StockFilters>,
    label?: { key: string; value: string },
  ): void;
  setSearch(value: string): void;
  page(offset: number): void;
  reset(clearPresentation?: boolean): void;
}
export function useStockAccountingState(
  kind: Ref<StockReadKind>,
): StockAccountingState {
  const route = useRoute(),
    router = useRouter();
  const parsed = computed(() =>
    readStockAccountingQuery(route.query, kind.value),
  );
  const params = computed(() => parsed.value.params),
    error = computed(() => parsed.value.error),
    search = ref(params.value.filters.search ?? "");
  let timer: ReturnType<typeof setTimeout> | undefined;
  watch(
    () => route.query,
    () => {
      clearTimeout(timer);
      search.value = params.value.filters.search ?? "";
    },
  );
  onScopeDispose(() => clearTimeout(timer));
  function patch(
    value: Partial<StockFilters>,
    label?: { key: string; value: string },
  ): void {
    clearTimeout(timer);
    const location = stockReadLocation(
      kind.value,
      changeStockFilters(params.value.filters, value),
    );
    const labels = Object.fromEntries(
      Object.entries(route.query).filter(
        ([key]) => key.endsWith("_label") && !!location.query[key.slice(0, -6)],
      ),
    );
    void router.replace({
      ...location,
      query: {
        ...(typeof route.query.tracking_columns === "string"
          ? { tracking_columns: route.query.tracking_columns }
          : {}),
        ...(route.query.stock_view === "positions"
          ? { stock_view: "positions" }
          : {}),
        ...labels,
        ...location.query,
        ...(label ? { [label.key + "_label"]: label.value } : {}),
      },
    });
  }
  function setSearch(value: string): void {
    search.value = value;
    clearTimeout(timer);
    timer = setTimeout(() => patch({ search: value.trim() }), 250);
  }
  function page(offset: number): void {
    void router.replace({
      query: { ...route.query, offset: String(Math.max(0, offset)) },
    });
  }
  function reset(clearPresentation = false): void {
    clearTimeout(timer);
    search.value = "";
    void router.replace({
      name: `inventory-stock-${kind.value}`,
      query: clearPresentation
        ? {}
        : {
            tracking_columns: route.query.tracking_columns,
            stock_view: route.query.stock_view,
          },
    });
  }
  return { params, error, search, setSearch, patch, page, reset };
}
