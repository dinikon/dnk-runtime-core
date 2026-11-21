<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{ sku?: string; busy: boolean; createDisabled: boolean }>();
const emit = defineEmits<{ back: []; create: []; refresh: [] }>();
</script>
<template>
  <header class="flex flex-wrap items-start gap-3">
    <Button variant="outline" :disabled="busy" @click="emit('back')"
      >Назад к SKU</Button
    >
    <div class="min-w-0 flex-1">
      <h1 class="text-xl font-semibold">Партии SKU</h1>
      <p class="break-all font-mono text-sm">{{ sku }}</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <Button variant="outline" :disabled="busy" @click="emit('refresh')"
        >Обновить</Button
      ><Button :disabled="busy || createDisabled" @click="emit('create')"
        >Создать партию</Button
      >
    </div>
  </header>
</template>
