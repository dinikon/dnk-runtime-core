<script setup lang="ts">
import { ArrowLeft } from "@lucide/vue";
import { Button } from "@/components/ui/button";
defineProps<{
  sku?: string;
  pending: boolean;
  packagingsDisabled: boolean;
  deleteDisabled?: boolean;
}>();
const emit = defineEmits<{
  back: [];
  packagings: [];
  lots: [];
  serials: [];
  delete: [];
}>();
</script>
<template>
  <header
    class="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-start gap-4 sm:flex sm:flex-wrap"
  >
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
        Код SKU, штрихкоды и параметры складского учёта.
      </p>
    </div>
    <div class="col-span-2 flex flex-wrap gap-2 sm:ml-auto">
      <Button
        type="button"
        variant="outline"
        :disabled="pending || packagingsDisabled"
        @click="emit('packagings')"
        >Упаковки</Button
      >
      <Button
        type="button"
        variant="outline"
        :disabled="pending || packagingsDisabled"
        @click="emit('lots')"
        >Партии</Button
      >
      <Button
        type="button"
        variant="outline"
        :disabled="pending || packagingsDisabled"
        @click="emit('serials')"
        >Серийные экземпляры</Button
      >
      <Button
        type="button"
        variant="destructive"
        :disabled="pending || deleteDisabled"
        @click="emit('delete')"
        >Удалить позицию</Button
      >
    </div>
  </header>
</template>
