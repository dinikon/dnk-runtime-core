<script setup lang="ts">
import { OffsetPagination } from "@/shared/pagination";
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
  <footer aria-label="Страницы источников">
    <OffsetPagination
      :page="page"
      :limit="limit"
      :total="total"
      :disabled="disabled"
      :limit-options="[20, 50, 100]"
      locale="ru"
      @change="emit('change', $event)"
    />
  </footer>
</template>
