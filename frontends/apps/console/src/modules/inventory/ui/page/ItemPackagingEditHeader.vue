<script setup lang="ts">
import { ArrowLeft } from "@lucide/vue";
import { Button } from "@/components/ui/button";
defineProps<{ code?: string; pending: boolean; deleteDisabled?: boolean }>();
const emit = defineEmits<{ back: []; delete: [] }>();
</script>
<template>
  <header class="flex min-w-0 flex-wrap items-start gap-4">
    <Button
      type="button"
      variant="outline"
      :disabled="pending"
      @click="emit('back')"
      ><ArrowLeft data-icon="inline-start" />Назад</Button
    >
    <div class="flex min-w-0 flex-1 flex-col gap-1">
      <h1 class="text-xl font-semibold">Редактирование упаковки</h1>
      <p v-if="code" class="break-all font-mono text-sm">{{ code }}</p>
      <p class="text-sm text-muted-foreground">
        Тип тары, код, название, количество и единица содержимого.
      </p>
    </div>
    <Button
      type="button"
      variant="destructive"
      :disabled="pending || deleteDisabled"
      @click="emit('delete')"
      >Удалить упаковку</Button
    >
  </header>
</template>
