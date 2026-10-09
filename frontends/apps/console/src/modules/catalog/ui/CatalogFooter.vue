<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{ page: number; total: number; pageSize: number }>();
defineEmits<{ page: [value: number] }>();
</script>
<template>
  <footer
    class="flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground"
  >
    <span>Всего: {{ total }} · Страница {{ page }}</span>
    <div class="flex gap-2">
      <Button
        variant="outline"
        :disabled="page <= 1"
        @click="$emit('page', page - 1)"
        >Назад</Button
      ><Button
        variant="outline"
        :disabled="page * pageSize >= total"
        @click="$emit('page', page + 1)"
        >Далее</Button
      >
    </div>
  </footer>
</template>
