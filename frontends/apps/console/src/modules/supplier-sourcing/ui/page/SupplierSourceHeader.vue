<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{ name: string | undefined; pending: boolean }>();
const emit = defineEmits<{ back: [] }>();
</script>
<template>
  <header class="flex flex-wrap items-start justify-between gap-3">
    <div>
      <h1 class="text-2xl font-semibold">
        {{ name ?? "Источник поставщика" }}
      </h1>
      <p class="mt-1 text-sm text-muted-foreground">
        Карточка и настройки внешнего источника
      </p>
    </div>
    <Button variant="outline" :disabled="pending" @click="emit('back')"
      >К списку источников</Button
    >
  </header>
</template>
