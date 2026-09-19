<script setup lang="ts">
import { ChevronLeft, ChevronRight } from "@lucide/vue";
import { Button } from "@/components/ui/button";

defineProps<{ total: number; page: number; totalPages: number }>();
defineEmits<{ page: [value: number] }>();
</script>

<template>
  <footer class="flex shrink-0 items-center justify-between text-sm">
    <span class="text-muted-foreground">Найдено: {{ total }}</span>
    <div class="flex items-center gap-2"><Button variant="outline" size="icon" :disabled="page <= 1" @click="$emit('page', page - 1)"><ChevronLeft /></Button><span>{{ page }} / {{ totalPages }}</span><Button variant="outline" size="icon" :disabled="page >= totalPages" @click="$emit('page', page + 1)"><ChevronRight /></Button></div>
  </footer>
</template>
