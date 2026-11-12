<script setup lang="ts">
import { ArrowLeft } from "@lucide/vue";
import { Button } from "@/components/ui/button";
defineProps<{ sku?: string; pending: boolean }>();
const emit = defineEmits<{ back: [] }>();
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
      <h1 class="text-xl font-semibold">Настройки SKU</h1>
      <p v-if="sku" class="break-all font-mono text-sm">{{ sku }}</p>
      <p class="text-sm text-muted-foreground">
        Единица измерения, шаг количества и правила складского учёта.
      </p>
    </div>
  </header>
</template>
