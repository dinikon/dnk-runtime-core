<script setup lang="ts">
import StockAccountingBody from "../ui/results/StockAccountingBody.vue";
import { useListStockBalances } from "../model/use-stock-accounting-queries";
import type { ListStockBalancesItem } from "../model/stock-accounting.types";
import { stockReadLocation } from "../model/stock-accounting-navigation";
import StockBalancesTable from "../ui/results/StockBalancesTable.vue";
import {
  stockAccountingPageOffset,
  readTrackingColumns,
  trackingColumnsQuery,
} from "../model/stock-accounting-state";
import type { StockTrackingColumns } from "../model/stock-accounting.types";
import StockTrackingColumnsControl from "../ui/results/StockTrackingColumnsControl.vue";
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { StockAccountingRequestError } from "../api/stock-accounting.api";
import { useInventoryScope } from "../model/use-inventory-scope";
import { useStockAccountingState } from "../model/use-stock-accounting-state";
import { useStockAccountingPicker } from "../model/use-stock-accounting-picker";
import {
  useListStockPositions,
  useListStockMovements,
  useListStockExecutions,
  useListStockPostings,
} from "../model/use-stock-accounting-queries";
import type {
  StockReadKind,
  StockFilterOption,
} from "../model/stock-accounting.types";
import {
  accountingTarget,
  stockFilterKeys,
  type StockAccountingTarget,
} from "../model/stock-accounting-navigation";
import StockPositionsTable from "../ui/results/StockPositionsTable.vue";
import StockMovementsTable from "../ui/results/StockMovementsTable.vue";
import StockFactsTable from "../ui/results/StockFactsTable.vue";
import StockAccountingPager from "../ui/results/StockAccountingPager.vue";
import StockAccountingFilters from "../ui/forms/StockAccountingFilters.vue";
import StockAccountingFilterDialog from "../ui/forms/StockAccountingFilterDialog.vue";
const props = defineProps<{ kind: StockReadKind }>(),
  kind = computed(() => props.kind),
  scope = useInventoryScope(),
  router = useRouter(),
  route = useRoute(),
  state = useStockAccountingState(kind);
const enabled = computed(() => !state.error.value),
  filters = computed(() => state.params.value.filters),
  picker = useStockAccountingPicker(filters, scope);
const trackingColumns = computed(() =>
  readTrackingColumns(route.query.tracking_columns),
);
function setTrackingColumns(value: StockTrackingColumns): void {
  void router.replace({
    query: { ...route.query, tracking_columns: trackingColumnsQuery(value) },
  });
}
const summary = computed(
  () => kind.value === "positions" && route.query.stock_view !== "positions",
);
const balanceParams = computed(() => ({
  ...state.params.value,
  groupByLot: trackingColumns.value.lot,
  groupBySerial: trackingColumns.value.serial,
}));
const balances = useListStockBalances(
  balanceParams,
  scope,
  computed(() => enabled.value && summary.value),
);
const positions = useListStockPositions(
  state.params,
  scope,
  computed(() => enabled.value && kind.value === "positions" && !summary.value),
);
const movements = useListStockMovements(
  state.params,
  scope,
  computed(() => enabled.value && kind.value === "movements"),
);
const executions = useListStockExecutions(
  state.params,
  scope,
  computed(() => enabled.value && kind.value === "executions"),
);
const postings = useListStockPostings(
  state.params,
  scope,
  computed(() => enabled.value && kind.value === "postings"),
);
const active = computed(() =>
  kind.value === "positions" && summary.value
    ? balances
    : { positions, movements, executions, postings }[kind.value],
);
const inaccessible = computed(
  () =>
    active.value.error.value instanceof StockAccountingRequestError &&
    [403, 404].includes(active.value.error.value.status ?? 0),
);
const total = computed(() => active.value.data.value?.total ?? 0),
  loading = computed(
    () => active.value.isPending.value && scope.ready.value && enabled.value,
  ),
  fetching = computed(() => active.value.isFetching.value),
  error = computed(
    () =>
      scope.error.value ||
      state.error.value ||
      active.value.error.value?.message ||
      "",
  );
const titles = {
  positions: "Физические остатки",
  movements: "Движения",
  executions: "Исполнения",
  postings: "Проводки",
};
const labels = computed(() =>
  Object.fromEntries(
    Object.entries(route.query).filter(
      (entry): entry is [string, string] => typeof entry[1] === "string",
    ),
  ),
);
watch(
  () => [total.value, fetching.value],
  () => {
    if (fetching.value || error.value || !active.value.data.value) return;
    const offset = stockAccountingPageOffset(
      state.params.value.offset,
      total.value,
    );
    if (offset !== state.params.value.offset) state.page(offset);
  },
);

watch(
  scope.key,
  (next, previous) => {
    picker.close();
    if (
      previous[0] &&
      previous[1] &&
      next.some((value, index) => value !== previous[index])
    )
      state.reset(true);
  },
  { flush: "sync" },
);
function navigate(target: StockAccountingTarget): void {
  void router.push(accountingTarget(target));
}
function select(option: StockFilterOption): void {
  const key = picker.kind.value;
  if (key)
    state.patch(
      { [key]: option.id },
      { key: stockFilterKeys[key], value: option.label },
    );
  picker.close();
}
function refresh(): void {
  void active.value.refetch();
}
function drillPositions(row: ListStockBalancesItem): void {
  const target = stockReadLocation("positions", {
    ...state.params.value.filters,
    inventoryItemId: row.inventoryItemId,
    warehouseId: row.warehouseId,
    locationId: row.locationId,
    ownerId: row.ownerId,
    stockStatus: row.stockStatus,
    lotId: row.lotId ?? state.params.value.filters.lotId,
    serialId: row.serialId ?? state.params.value.filters.serialId,
  });
  void router.push({
    ...target,
    query: {
      ...target.query,
      stock_view: "positions",
      tracking_columns: trackingColumnsQuery(trackingColumns.value),
    },
  });
}
function stockView(value: "summary" | "positions"): void {
  void router.replace({
    query: {
      ...route.query,
      stock_view: value === "positions" ? "positions" : undefined,
      offset: undefined,
    },
  });
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Физический учёт"
  >
    <header class="flex shrink-0 flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">{{ titles[kind] }}</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Физическое количество на складах. Доступность с учётом резервов здесь
          не рассчитывается.
        </p>
      </div>
      <Button
        variant="outline"
        :disabled="fetching || !scope.ready.value || !enabled"
        @click="refresh"
        >Обновить</Button
      >
    </header>
    <nav class="flex shrink-0 flex-wrap gap-2" aria-label="Представления учёта">
      <Button
        v-for="(title, key) in titles"
        :key="key"
        :variant="key === kind ? 'default' : 'outline'"
        @click="
          router.push({
            name: 'inventory-stock-' + key,
            query: {
              ...route.query,
              include_zero: undefined,
              offset: undefined,
            },
          })
        "
        >{{ title }}</Button
      >
    </nav>
    <div
      v-if="kind === 'positions'"
      class="flex shrink-0 flex-wrap items-center gap-2"
    >
      <Button
        :variant="summary ? 'default' : 'outline'"
        @click="stockView('summary')"
        >Сводка</Button
      ><Button
        :variant="summary ? 'outline' : 'default'"
        @click="stockView('positions')"
        >Физические позиции</Button
      >
      <p class="text-xs text-muted-foreground">
        В сводке партии и серии объединены. Включите столбец для детализации.
      </p>
    </div>
    <StockAccountingFilters
      :filters="filters"
      :kind="kind"
      :search="state.search.value"
      :labels="labels"
      @patch="state.patch"
      @search="state.setSearch"
      @pick="picker.open"
      @reset="state.reset"
    />
    <StockTrackingColumnsControl
      v-if="kind === 'positions' || kind === 'movements'"
      :columns="trackingColumns"
      @change="setTrackingColumns"
    />
    <StockAccountingBody
      :loading="loading"
      :error="error"
      :has-data="
        scope.ready.value && enabled && !inaccessible && !!active.data.value
      "
      :empty="!active.data.value?.items.length"
      :can-retry="!fetching && scope.ready.value && enabled"
      :fetching="fetching"
      @retry="refresh"
    >
      <StockBalancesTable
        v-if="summary"
        :columns="trackingColumns"
        :items="balances.data.value?.items ?? []"
        @positions="drillPositions"
        @navigate="navigate"
      /><StockPositionsTable
        :columns="trackingColumns"
        v-else-if="kind === 'positions'"
        :items="positions.data.value?.items ?? []"
        @status-change="
          router.push({
            name: 'inventory-status-change-create',
            query: { source_position_id: $event },
          })
        "
        @navigate="navigate"
      /><StockMovementsTable
        :columns="trackingColumns"
        v-else-if="kind === 'movements'"
        :items="movements.data.value?.items ?? []"
        @navigate="navigate"
      /><StockFactsTable
        v-else
        :kind="kind"
        :items="
          kind === 'executions'
            ? (executions.data.value?.items ?? [])
            : (postings.data.value?.items ?? [])
        "
        @navigate="navigate"
      />
      <template #footer
        ><StockAccountingPager
          :offset="state.params.value.offset"
          :limit="20"
          :total="total"
          :busy="fetching"
          @page="state.page"
      /></template>
    </StockAccountingBody>
    <StockAccountingFilterDialog
      v-if="picker.kind.value"
      :kind="picker.kind.value"
      :search="picker.search.value"
      :page="picker.page.value"
      :offset="picker.offset.value"
      :loading="picker.loading.value"
      :error="picker.error.value"
      @close="picker.close"
      @search="picker.setSearch"
      @page="picker.offset.value = $event"
      @select="select"
      @retry="picker.retry"
    />
  </section>
</template>
