<script setup lang="ts">
import type { StockTrackingColumns } from "../../model/stock-accounting.types";
defineProps<{ columns: StockTrackingColumns }>();
const emit = defineEmits<{ change: [columns: StockTrackingColumns] }>();
</script>
<template>
  <details class="self-start rounded-md border px-3 py-2">
    <summary class="cursor-pointer text-sm">Столбцы</summary>
    <fieldset class="mt-2 flex flex-wrap gap-4 text-sm">
      <legend class="sr-only">Столбцы прослеживаемости</legend>
      <label class="flex items-center gap-2"
        ><input
          type="checkbox"
          :checked="columns.lot"
          @change="
            emit('change', {
              ...columns,
              lot: ($event.target as HTMLInputElement).checked,
            })
          "
        />Партия</label
      ><label class="flex items-center gap-2"
        ><input
          type="checkbox"
          :checked="columns.serial"
          @change="
            emit('change', {
              ...columns,
              serial: ($event.target as HTMLInputElement).checked,
            })
          "
        />Серия</label
      >
    </fieldset>
  </details>
</template>
