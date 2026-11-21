<script setup lang="ts">
import { Plus, RefreshCw, ArrowLeft } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/custom-ui/page-header";
import { cn } from "@/lib/utils";
defineProps<{
  refreshing: boolean;
  disabled: boolean;
  createDisabled: boolean;
  pending: boolean;
}>();
const emit = defineEmits<{ back: []; refresh: []; create: [] }>();
</script>
<template>
  <PageHeader
    compact
    title="Упаковки SKU"
    description="Варианты тары с количеством и единицей содержимого."
    ><template #actions
      ><div class="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          :disabled="pending"
          @click="emit('back')"
          ><ArrowLeft data-icon="inline-start" />Назад</Button
        >
        <Button type="button" :disabled="createDisabled" @click="emit('create')"
          ><Plus data-icon="inline-start" />Создать упаковку</Button
        >
        <Button
          type="button"
          variant="outline"
          :disabled="disabled || pending"
          @click="emit('refresh')"
          ><RefreshCw
            data-icon="inline-start"
            :class="cn(refreshing && 'animate-spin')"
          />Обновить</Button
        >
      </div></template
    ></PageHeader
  >
</template>
