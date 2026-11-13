<script setup lang="ts">
import { PackageOpen } from "@lucide/vue";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/custom-ui/empty-state";
import type { StockLocation } from "../../model/stock-location.types";
import StockLocationsTable from "./StockLocationsTable.vue";

defineProps<{
  items: readonly StockLocation[];
  loading: boolean;
  refreshing: boolean;
  error: string;
  canRetry: boolean;
  retryPending: boolean;
  filtered: boolean;
  outOfRange: boolean;
  defaultLocationId: string | null | undefined;
}>();
const emit = defineEmits<{
  retry: [];
  clear: [];
  firstPage: [];
  edit: [id: string];
  children: [id: string];
}>();
</script>

<template>
  <div
    class="flex min-h-40 min-w-0 flex-1 flex-col gap-3 md:min-h-0"
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
      Обновление локаций…
    </p>
    <StockLocationsTable
      v-if="items.length"
      :items="items"
      :default-location-id="defaultLocationId"
      @edit="emit('edit', $event)"
      @children="emit('children', $event)"
    />
    <div
      v-else-if="loading"
      role="status"
      aria-label="Загрузка локаций"
      class="flex flex-col gap-2"
    >
      <Skeleton class="h-10 w-full" />
      <Skeleton v-for="row in 6" :key="row" class="h-10 w-full" />
    </div>
    <div v-else-if="!error" class="min-h-0 flex-1 overflow-auto">
      <EmptyState
        v-if="outOfRange"
        :icon="PackageOpen"
        title="На этой странице нет локаций"
        description="Вернитесь на первую страницу списка."
        primary-action-label="На первую страницу"
        @primary-action="emit('firstPage')"
      />
      <EmptyState
        v-else-if="filtered"
        :icon="PackageOpen"
        title="Ничего не найдено"
        description="Измените поиск или фильтры."
        primary-action-label="Сбросить фильтры"
        @primary-action="emit('clear')"
      />
      <EmptyState
        v-else
        :icon="PackageOpen"
        title="Локаций пока нет"
        description="Создайте локацию выбранного склада."
      />
    </div>
  </div>
</template>
