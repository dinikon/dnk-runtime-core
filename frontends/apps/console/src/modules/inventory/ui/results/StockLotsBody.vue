<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import type { StockLot } from "../../model/stock-lot.types";
import StockLotsTable from "./StockLotsTable.vue";
defineProps<{
  items: readonly StockLot[];
  loading: boolean;
  refreshing: boolean;
  error: string;
  disabled: boolean;
  filtered: boolean;
  outOfRange: boolean;
  canRetry: boolean;
}>();
const emit = defineEmits<{
  retry: [];
  clear: [];
  firstPage: [];
  open: [id: string];
}>();
</script>
<template>
  <div
    class="flex min-h-40 min-w-0 flex-1 flex-col gap-3"
    :aria-busy="loading || refreshing"
  >
    <Alert v-if="error" variant="destructive"
      ><AlertDescription class="flex flex-wrap items-center gap-3"
        ><span>{{ error }}</span
        ><Button
          v-if="canRetry"
          variant="outline"
          :disabled="refreshing || disabled"
          @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <p v-if="refreshing" role="status" class="text-sm text-muted-foreground">
      Обновление партий…
    </p>
    <StockLotsTable
      v-if="items.length"
      :items="items"
      :disabled="disabled"
      @open="emit('open', $event)"
    />
    <div
      v-else-if="loading"
      role="status"
      aria-label="Загрузка партий"
      class="flex flex-col gap-2"
    >
      <Skeleton v-for="row in 5" :key="row" class="h-10 w-full" />
    </div>
    <div v-else-if="!error" class="rounded-md border p-6 text-center">
      <template v-if="outOfRange"
        ><p>На этой странице нет партий.</p>
        <Button variant="link" @click="emit('firstPage')"
          >На первую страницу</Button
        ></template
      >
      <template v-else-if="filtered"
        ><p>Партии не найдены.</p>
        <Button variant="link" @click="emit('clear')"
          >Сбросить поиск</Button
        ></template
      >
      <p v-else>Партий пока нет.</p>
    </div>
  </div>
</template>
