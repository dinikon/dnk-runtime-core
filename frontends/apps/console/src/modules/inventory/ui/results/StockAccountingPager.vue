<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{ offset: number; limit: number; total: number; busy: boolean }>();
const emit = defineEmits<{ page: [offset: number] }>();
</script>
<template>
  <footer class="flex flex-wrap items-center justify-between gap-2">
    <Button
      variant="outline"
      :disabled="busy || offset === 0"
      @click="emit('page', Math.max(0, offset - limit))"
      >Назад</Button
    ><span class="text-sm text-muted-foreground"
      >{{ total ? Math.min(offset + 1, total) : 0 }}–{{
        Math.min(offset + limit, total)
      }}
      из {{ total }}</span
    ><Button
      variant="outline"
      :disabled="busy || offset + limit >= total"
      @click="emit('page', offset + limit)"
      >Далее</Button
    >
  </footer>
</template>
