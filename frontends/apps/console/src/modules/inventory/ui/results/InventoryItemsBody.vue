<script setup lang="ts">
import { PackageOpen } from "@lucide/vue";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/custom-ui/empty-state";
import type { InventoryItemListRow } from "../../model/inventory-item.types";
import InventoryItemsTable from "./InventoryItemsTable.vue";

defineProps<{
  items: readonly InventoryItemListRow[];
  loading: boolean;
  refreshing: boolean;
  error: string;
  canRetry: boolean;
  retryPending: boolean;
  filtered: boolean;
  outOfRange: boolean;
  disabled?: boolean;
}>();
const emit = defineEmits<{
  retry: [];
  clear: [];
  firstPage: [];
  edit: [id: string];
  packagings: [id: string];
  delete: [item: InventoryItemListRow];
}>();
</script>

<template>
  <div
    class="flex min-h-0 min-w-0 flex-1 flex-col gap-3"
    :aria-busy="loading || refreshing"
  >
    <Alert v-if="error" variant="destructive" class="shrink-0">
      <AlertDescription
        class="flex flex-wrap items-center justify-between gap-3"
      >
        <span>{{ error }}</span>
        <Button
          v-if="canRetry"
          type="button"
          variant="outline"
          size="sm"
          :disabled="retryPending"
          @click="emit('retry')"
          >Повторить</Button
        >
      </AlertDescription>
    </Alert>
    <p
      v-if="refreshing"
      role="status"
      class="shrink-0 text-sm text-muted-foreground"
    >
      Обновление номенклатуры…
    </p>
    <InventoryItemsTable
      v-if="items.length"
      :items="items"
      :disabled="disabled"
      @delete="emit('delete', $event)"
      @edit="emit('edit', $event)"
      @packagings="emit('packagings', $event)"
    />
    <div
      v-else-if="loading"
      role="status"
      aria-label="Загрузка складской номенклатуры"
      class="flex flex-col gap-2"
    >
      <Skeleton class="h-10 w-full" />
      <Skeleton v-for="row in 6" :key="row" class="h-10 w-full" />
    </div>
    <div v-else-if="!error" class="min-h-0 flex-1 overflow-auto">
      <EmptyState
        v-if="outOfRange"
        :icon="PackageOpen"
        title="На этой странице нет позиций"
        description="Вернитесь на первую страницу списка."
        primary-action-label="На первую страницу"
        @primary-action="emit('firstPage')"
      />
      <EmptyState
        v-else-if="filtered"
        :icon="PackageOpen"
        title="Ничего не найдено"
        description="Измените SKU в поиске или очистите запрос."
        primary-action-label="Сбросить поиск"
        @primary-action="emit('clear')"
      />
      <EmptyState
        v-else
        :icon="PackageOpen"
        title="Номенклатура пока пуста"
        description="Здесь появятся складские позиции с единицами измерения и правилами учёта."
      />
    </div>
  </div>
</template>
