<script setup lang="ts">
import { Plus, RefreshCw } from "@lucide/vue";
import { PageHeader } from "@/components/custom-ui/page-header";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

defineProps<{
  refreshing: boolean;
  disabled: boolean;
  createDisabled: boolean;
}>();
const emit = defineEmits<{ refresh: []; create: [] }>();
</script>

<template>
  <PageHeader
    compact
    title="Складская номенклатура"
    description="Единицы измерения и правила складского учёта."
  >
    <template #actions>
      <div
        class="flex w-full flex-none flex-wrap items-center gap-2 @2xl/page-header:w-auto"
      >
        <Button type="button" :disabled="createDisabled" @click="emit('create')"
          ><Plus data-icon="inline-start" />Создать</Button
        >
        <Button
          type="button"
          variant="outline"
          :disabled="disabled"
          @click="emit('refresh')"
        >
          <RefreshCw
            data-icon="inline-start"
            :class="cn(refreshing && 'animate-spin')"
            aria-hidden="true"
          />
          Обновить
        </Button>
      </div>
    </template>
  </PageHeader>
</template>
