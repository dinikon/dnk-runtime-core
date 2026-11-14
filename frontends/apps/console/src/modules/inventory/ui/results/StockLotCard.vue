<script setup lang="ts">
import type { StockLot } from "../../model/stock-lot.types";
import { displayStockDate } from "../../model/stock-lot.validation";
defineProps<{ lot: StockLot }>();
</script>
<template>
  <dl class="grid gap-4 rounded-md border p-5 sm:grid-cols-2">
    <div class="min-w-0 sm:col-span-2">
      <dt class="text-sm text-muted-foreground">Номер партии</dt>
      <dd class="break-all font-mono">{{ lot.number }}</dd>
    </div>
    <div>
      <dt class="text-sm text-muted-foreground">Дата производства</dt>
      <dd>{{ displayStockDate(lot.manufacturedOn) }}</dd>
    </div>
    <div>
      <dt class="text-sm text-muted-foreground">Срок годности</dt>
      <dd>{{ displayStockDate(lot.expiresOn) }}</dd>
    </div>
  </dl>
</template>
