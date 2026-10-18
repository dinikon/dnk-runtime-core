<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{
  page: number;
  total: number;
  limit: number;
  pending?: boolean;
}>();
defineEmits<{ change: [page: number] }>();
</script>
<template>
  <footer
    class="flex flex-wrap items-center justify-between gap-3 py-4 text-sm"
  >
    <span class="text-muted-foreground"
      >Записей: {{ total }} · Страница {{ page }} из
      {{ Math.max(1, Math.ceil(total / limit)) }}</span
    >
    <div class="flex gap-2">
      <Button
        variant="outline"
        size="sm"
        :disabled="page <= 1 || pending"
        @click="$emit('change', page - 1)"
        >Назад</Button
      ><Button
        variant="outline"
        size="sm"
        :disabled="page * limit >= total || pending"
        @click="$emit('change', page + 1)"
        >Далее</Button
      >
    </div>
  </footer>
</template>
