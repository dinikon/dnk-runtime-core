<script setup lang="ts">
import StockAccountingBody from "./StockAccountingBody.vue";
import StockAccountingPager from "./StockAccountingPager.vue";
import StockMovementsTable from "./StockMovementsTable.vue";
import StockTrackingColumnsControl from "./StockTrackingColumnsControl.vue";
import type {
  ListStockMovementsResult,
  StockTrackingColumns,
} from "../../model/stock-accounting.types";
import type { StockAccountingTarget } from "../../model/stock-accounting-navigation";
defineProps<{
  history: ListStockMovementsResult | undefined;
  matching: boolean;
  loading: boolean;
  error: string;
  fetching: boolean;
  canRetry: boolean;
  offset: number;
  columns: StockTrackingColumns;
}>();
const emit = defineEmits<{
  page: [offset: number];
  navigate: [target: StockAccountingTarget];
  columns: [value: StockTrackingColumns];
  retry: [];
}>();
</script>
<template>
  <section class="flex min-w-0 shrink-0 flex-col gap-4">
    <h2 class="text-lg font-semibold">История позиции</h2>
    <StockTrackingColumnsControl
      :columns="columns"
      @change="emit('columns', $event)"
    /><StockAccountingBody
      :loading="loading || !matching"
      :error="error"
      :has-data="matching && !!history"
      :empty="!history?.items.length"
      :can-retry="canRetry"
      :fetching="fetching"
      :loading-text="
        matching
          ? 'Загрузка истории…'
          : 'Остаток изменился. Согласовываем историю…'
      "
      empty-text="Движений на этой странице нет."
      @retry="emit('retry')"
      ><StockMovementsTable
        :items="history?.items ?? []"
        :columns="columns"
        @navigate="emit('navigate', $event)" /><template #footer
        ><StockAccountingPager
          :offset="offset"
          :limit="20"
          :total="history?.total ?? 0"
          :busy="fetching"
          @page="emit('page', $event)" /></template
    ></StockAccountingBody>
  </section>
</template>
