<script setup lang="ts">
import { Button } from "@/components/ui/button";
defineProps<{ disabled: boolean; refreshing: boolean }>();
const emit = defineEmits<{ create: []; refresh: [] }>();
</script>
<template>
  <header class="flex flex-wrap items-start justify-between gap-3">
    <div>
      <h1 class="text-2xl font-semibold">Источники поставщиков</h1>
      <p class="mt-1 text-sm text-muted-foreground">
        Внешние склады и каналы поставки, способы исполнения и актуальность
        наличия.
      </p>
    </div>
    <div class="flex gap-2">
      <Button
        variant="outline"
        :disabled="disabled || refreshing"
        @click="emit('refresh')"
        >Обновить</Button
      ><Button :disabled="disabled" @click="emit('create')"
        >Создать источник</Button
      >
    </div>
  </header>
</template>
