<script setup lang="ts">
import StockTrackingColumnsControl from "./StockTrackingColumnsControl.vue";
import { Button } from "@/components/ui/button";
import StockBalancesTable from "./StockBalancesTable.vue";
import StockMovementsTable from "./StockMovementsTable.vue";
import type {
  StockTrackingColumns,
  ListStockBalancesItem,
} from "../../model/stock-accounting.types";
import type {
  ListStockBalancesResult,
  ListStockMovementsResult,
} from "../../model/stock-accounting.types";
import type { StockAccountingTarget } from "../../model/stock-accounting-navigation";
defineProps<{
  columns: StockTrackingColumns;
  positions: ListStockBalancesResult | undefined;
  movements: ListStockMovementsResult | undefined;
  loading: boolean;
  error: string;
}>();
const emit = defineEmits<{
  navigate: [target: StockAccountingTarget];
  all: [kind: "positions" | "movements"];
  retry: [];
  columns: [value: StockTrackingColumns];
  positions: [row: ListStockBalancesItem];
}>();
</script>
<template>
  <section
    class="flex min-w-0 shrink-0 flex-col gap-4 rounded-lg border p-4"
    aria-label="Связанный физический учёт"
  >
    <h2 class="text-lg font-semibold">Физические остатки и движения</h2>
    <p class="text-sm text-muted-foreground">
      Показаны первые пять записей. Физический запас не равен доступности с
      учётом резервов.
    </p>
    <p v-if="loading" role="status">Загрузка учёта…</p>
    <p v-if="error" role="alert" class="text-destructive">
      {{ error
      }}<Button variant="outline" @click="emit('retry')">Повторить</Button>
    </p>
    <StockTrackingColumnsControl
      :columns="columns"
      @change="emit('columns', $event)"
    />
    <h3 class="font-medium">Физические остатки</h3>
    <StockBalancesTable
      @positions="emit('positions', $event)"
      :columns="columns"
      v-if="positions?.items.length"
      :items="positions.items"
      @navigate="emit('navigate', $event)"
    />
    <p v-else-if="positions" class="text-sm text-muted-foreground">
      Положительных остатков нет.
    </p>
    <Button
      variant="outline"
      class="self-start"
      @click="emit('all', 'positions')"
      >Все остатки ({{ positions?.total ?? "…" }})</Button
    >
    <h3 class="font-medium">Движения</h3>
    <StockMovementsTable
      :columns="columns"
      v-if="movements?.items.length"
      :items="movements.items"
      @navigate="emit('navigate', $event)"
    />
    <p v-else-if="movements" class="text-sm text-muted-foreground">
      Движений нет.
    </p>
    <Button
      variant="outline"
      class="self-start"
      @click="emit('all', 'movements')"
      >Все движения ({{ movements?.total ?? "…" }})</Button
    >
  </section>
</template>
