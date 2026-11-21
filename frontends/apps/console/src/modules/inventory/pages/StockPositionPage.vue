<script setup lang="ts">
import StockAccountingBody from "../ui/results/StockAccountingBody.vue";
import StockPositionHistory from "../ui/results/StockPositionHistory.vue";
import StockPositionDetails from "../ui/results/StockPositionDetails.vue";
import {
  stockAccountingPageOffset,
  readTrackingColumns,
  trackingColumnsQuery,
} from "../model/stock-accounting-state";
import type { StockTrackingColumns } from "../model/stock-accounting.types";
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Button } from "@/components/ui/button";
import { StockAccountingRequestError } from "../api/stock-accounting.api";
import { useInventoryScope } from "../model/use-inventory-scope";
import {
  useGetStockPosition,
  useListStockMovements,
} from "../model/use-stock-accounting-queries";
import {
  accountingTarget,
  stockReadLocation,
  type StockAccountingTarget,
} from "../model/stock-accounting-navigation";
const route = useRoute(),
  router = useRouter(),
  scope = useInventoryScope(),
  id = computed(() =>
    typeof route.params.positionId === "string" ? route.params.positionId : "",
  );
const offset = computed(() => {
  const n = Number(route.query.history_offset ?? 0);
  return Number.isSafeInteger(n) && n >= 0 ? n : 0;
});
const query = useGetStockPosition(
  id,
  scope,
  computed(() => true),
);
const params = computed(() => ({
    filters: { positionId: id.value },
    offset: offset.value,
    limit: 20,
  })),
  history = useListStockMovements(
    params,
    scope,
    computed(() => !!id.value),
  );
const position = computed(() =>
  scope.ready.value &&
  !(
    query.error.value instanceof StockAccountingRequestError &&
    [403, 404].includes(query.error.value.status ?? 0)
  )
    ? query.data.value
    : undefined,
);
const historyReadable = computed(
  () =>
    !(
      history.error.value instanceof StockAccountingRequestError &&
      [403, 404].includes(history.error.value.status ?? 0)
    ),
);
const matching = computed(
  () =>
    !position.value ||
    !history.data.value?.position ||
    position.value.version === history.data.value.position.version,
);
watch(
  () => history.data.value?.position?.version,
  (version) => {
    if (
      version !== undefined &&
      position.value &&
      version !== position.value.version
    )
      void query.refetch();
  },
);
watch(
  () => [history.data.value?.total, history.isFetching.value],
  () => {
    if (
      history.isFetching.value ||
      history.error.value ||
      !history.data.value ||
      !matching.value
    )
      return;
    const next = stockAccountingPageOffset(
      offset.value,
      history.data.value.total,
    );
    if (next !== offset.value) page(next);
  },
);
function navigate(target: StockAccountingTarget): void {
  void router.push(accountingTarget(target));
}
function page(value: number): void {
  void router.replace({
    query: { ...route.query, history_offset: String(value) },
  });
}
function refresh(): void {
  void query.refetch();
  void history.refetch();
}
const trackingColumns = computed(() =>
  readTrackingColumns(route.query.tracking_columns),
);
function setTrackingColumns(value: StockTrackingColumns): void {
  void router.replace({
    query: { ...route.query, tracking_columns: trackingColumnsQuery(value) },
  });
}
</script>
<template>
  <section
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-5 overflow-y-auto"
    aria-label="Карточка физической позиции"
  >
    <header class="flex shrink-0 flex-wrap justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">Физическая позиция</h1>
        <p class="mt-1 text-sm text-muted-foreground">
          Физический остаток. Резервы и доступность к продаже не рассчитываются.
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <Button
          v-if="
            position &&
            /[1-9]/.test(position.onHandQty.split(/[eE]/)[0] ?? '') &&
            position.warehouseIsActive &&
            position.locationIsActive
          "
          :disabled="
            query.isFetching.value || !!query.error.value || !scope.ready.value
          "
          @click="
            router.push({
              name: 'inventory-status-change-create',
              query: { source_position_id: position.id },
            })
          "
          >Изменить состояние</Button
        >
        <Button
          variant="outline"
          @click="router.push(stockReadLocation('positions', {}))"
          >К остаткам</Button
        ><Button
          variant="outline"
          :disabled="
            query.isFetching.value ||
            history.isFetching.value ||
            !scope.ready.value
          "
          @click="refresh"
          >Обновить</Button
        >
      </div>
    </header>
    <StockAccountingBody
      :loading="query.isPending.value && scope.ready.value"
      :error="scope.error.value || query.error.value?.message || ''"
      :has-data="!!position"
      :empty="false"
      :can-retry="scope.ready.value && !query.isFetching.value"
      :fetching="query.isFetching.value"
      loading-text="Загрузка позиции…"
      @retry="refresh"
    >
      <StockPositionDetails
        v-if="position"
        :position="position"
        @navigate="navigate"
      />
      <StockPositionHistory
        :history="historyReadable ? history.data.value : undefined"
        :matching="matching"
        :loading="history.isPending.value && scope.ready.value"
        :error="history.error.value?.message || ''"
        :fetching="history.isFetching.value"
        :can-retry="scope.ready.value && !history.isFetching.value"
        :offset="offset"
        :columns="trackingColumns"
        @columns="setTrackingColumns"
        @navigate="navigate"
        @page="page"
        @retry="refresh"
      />
    </StockAccountingBody>
  </section>
</template>
