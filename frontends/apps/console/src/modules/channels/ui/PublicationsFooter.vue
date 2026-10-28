<script setup lang="ts">
import { OffsetPagination } from "@/shared/pagination";
import { Button } from "@/components/ui/button";
import { publicationPageSizes } from "../model/publication.filters";

defineProps<{
  offset: number;
  limit: number;
  total: number | undefined;
  pending: boolean;
}>();
const emit = defineEmits<{
  change: [value: { page: number; limit: number }];
}>();
</script>

<template>
  <footer
    class="sticky bottom-0 z-20 shrink-0 bg-background pb-1"
    aria-label="Навигация по публикациям"
  >
    <OffsetPagination
      v-if="total !== undefined"
      :page="Math.floor(offset / limit) + 1"
      :limit="limit"
      :limit-options="publicationPageSizes"
      :total="total"
      locale="ru"
      @change="emit('change', $event)"
    />
    <div
      v-else
      class="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <p class="text-sm text-muted-foreground" role="status">
        {{
          pending
            ? "Загружаем количество публикаций…"
            : "Количество публикаций недоступно"
        }}
      </p>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" disabled>Назад</Button>
        <span class="min-w-16 text-center text-sm text-muted-foreground"
          >—</span
        >
        <Button variant="outline" size="sm" disabled>Вперёд</Button>
      </div>
    </div>
  </footer>
</template>
