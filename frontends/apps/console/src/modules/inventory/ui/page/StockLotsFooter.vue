<script setup lang="ts">
import { OffsetPagination } from "@/shared/pagination";
import { STOCK_LOT_PAGE_SIZES } from "../../model/stock-lot.constants";

defineProps<{
  page: number;
  limit: number;
  total: number;
  disabled: boolean;
}>();
const emit = defineEmits<{
  change: [value: { page: number; limit: number }];
}>();
</script>

<template>
  <footer class="shrink-0" aria-label="Страницы списка партий">
    <OffsetPagination
      :page="page"
      :limit="limit"
      :total="total"
      :disabled="disabled"
      :limit-options="[...STOCK_LOT_PAGE_SIZES]"
      locale="ru"
      @change="emit('change', $event)"
    />
  </footer>
</template>
