<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{
  offset: number;
  limit: number;
  total: number;
  pending: boolean;
}>();
const emit = defineEmits<{ page: [offset: number] }>();
</script>
<template>
  <footer class="flex flex-wrap items-center gap-3 text-sm">
    <Button
      variant="outline"
      :disabled="pending || !offset"
      @click="emit('page', Math.max(0, offset - limit))"
      >Назад</Button
    ><span
      >{{ total ? offset + 1 : 0 }}–{{ Math.min(offset + limit, total) }} из
      {{ total }}</span
    ><Button
      variant="outline"
      :disabled="pending || offset + limit >= total"
      @click="emit('page', offset + limit)"
      >Далее</Button
    >
  </footer>
</template>
