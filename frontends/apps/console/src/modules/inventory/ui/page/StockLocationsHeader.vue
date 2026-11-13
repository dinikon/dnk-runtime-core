<script setup lang="ts">
import { ArrowLeft, Plus, RefreshCw } from "@lucide/vue";
import { PageHeader } from "@/components/custom-ui/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Warehouse } from "../../model/warehouse.types";
defineProps<{
  warehouse?: Warehouse;
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
    title="Локации склада"
    :description="
      warehouse ? `${warehouse.code} — ${warehouse.name}` : 'Загрузка склада…'
    "
  >
    <template #actions
      ><div class="flex w-full flex-wrap gap-2 @2xl/page-header:w-auto">
        <Button
          type="button"
          variant="outline"
          :disabled="pending"
          @click="emit('back')"
          ><ArrowLeft data-icon="inline-start" />Назад</Button
        >
        <Button type="button" :disabled="createDisabled" @click="emit('create')"
          ><Plus data-icon="inline-start" />Создать локацию</Button
        >
        <Button
          type="button"
          variant="outline"
          class="size-9 shrink-0 sm:w-auto"
          aria-label="Обновить"
          :disabled="disabled"
          @click="emit('refresh')"
          ><RefreshCw data-icon="inline-start" /><span class="hidden sm:inline"
            >Обновить</span
          ></Button
        >
      </div></template
    >
  </PageHeader>
  <div
    v-if="warehouse"
    class="flex shrink-0 flex-wrap items-center gap-2 text-sm text-muted-foreground"
  >
    <Badge :variant="warehouse.isActive ? 'secondary' : 'outline'">{{
      warehouse.isActive ? "Склад активен" : "Склад неактивен"
    }}</Badge
    ><span v-if="!warehouse.isActive"
      >Создание локаций доступно после активации склада. Редактирование
      разрешено.</span
    >
  </div>
</template>
