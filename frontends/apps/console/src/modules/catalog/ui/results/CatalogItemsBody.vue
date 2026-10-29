<script setup lang="ts">
import { Package } from "@lucide/vue";
import { EmptyState } from "@/components/custom-ui/empty-state";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { CatalogListItem } from "../../model/catalog.types";
import CatalogItemsTable from "./CatalogItemsTable.vue";

defineProps<{
  items: readonly CatalogListItem[];
  loading: boolean;
  error: string;
  filtered: boolean;
  outOfRange: boolean;
  disabled: boolean;
  canCreate: boolean;
  imageUrl: (item: CatalogListItem) => string | undefined;
}>();
const emit = defineEmits<{
  open: [id: string];
  remove: [item: CatalogListItem];
  retry: [];
  reset: [];
  create: [];
  firstPage: [];
}>();
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-3" :aria-busy="loading">
    <Alert v-if="error" variant="destructive">
      <AlertDescription
        class="flex flex-wrap items-center justify-between gap-3"
        >{{ error
        }}<Button type="button" variant="outline" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      >
    </Alert>
    <div
      v-if="loading && !items.length"
      class="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden"
      role="status"
      aria-label="Загрузка товаров"
    >
      <Skeleton class="h-10 w-full shrink-0" /><Skeleton
        v-for="index in 8"
        :key="index"
        class="h-10 w-full shrink-0"
      />
    </div>
    <CatalogItemsTable
      v-else-if="items.length"
      :items="items"
      :disabled="disabled"
      :image-url="imageUrl"
      @open="emit('open', $event)"
      @remove="emit('remove', $event)"
    />
    <div v-else-if="!error && outOfRange" class="min-h-0 flex-1 overflow-auto">
      <EmptyState
        :icon="Package"
        title="На этой странице нет товаров"
        description="Перейдите на первую страницу текущей выборки."
        primary-action-label="На первую страницу"
        @primary-action="emit('firstPage')"
      />
    </div>
    <div v-else-if="!error" class="min-h-0 flex-1 overflow-auto">
      <EmptyState
        :icon="Package"
        :title="filtered ? 'Товары не найдены' : 'В каталоге пока нет товаров'"
        :description="
          filtered
            ? 'Измените поиск или статус, чтобы увидеть другие товары.'
            : 'Создайте первый товар или импортируйте позиции в каталог.'
        "
        :primary-action-label="filtered ? 'Сбросить фильтры' : 'Создать товар'"
        :primary-disabled="!filtered && !canCreate"
        @primary-action="filtered ? emit('reset') : emit('create')"
      />
    </div>
  </div>
</template>
