<script setup lang="ts">
import { Layers } from "@lucide/vue";
import { EmptyState } from "@/components/custom-ui/empty-state";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { CatalogListItem } from "../../model/catalog.types";
import type { CatalogQuickEditSection } from "../../model/catalog-table.types";
import CatalogItemsTable from "../results/CatalogItemsTable.vue";
import { catalogVariantsColumns } from "./catalog-variants.columns";

defineProps<{
  items: readonly CatalogListItem[];
  loading: boolean;
  error: string;
  disabled: boolean;
  canCreate: boolean;
  outOfRange: boolean;
  imageUrl: (item: CatalogListItem) => string | undefined;
  canQuickEdit: boolean;
}>();
const emit = defineEmits<{
  open: [id: string];
  remove: [id: string];
  retry: [];
  create: [];
  firstPage: [];
  quickEdit: [item: CatalogListItem, section: CatalogQuickEditSection];
}>();
</script>

<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-3" :aria-busy="loading">
    <Alert v-if="error" variant="destructive" class="shrink-0"
      ><AlertDescription
        class="flex flex-wrap items-center justify-between gap-3"
        >{{ error
        }}<Button type="button" variant="outline" @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <div
      v-if="loading && !items.length"
      class="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden"
      role="status"
      aria-label="Загрузка вариантов"
    >
      <Skeleton class="h-10 w-full shrink-0" /><Skeleton
        v-for="index in 8"
        :key="index"
        class="h-10 w-full shrink-0"
      />
    </div>
    <CatalogItemsTable
      v-else-if="items.length"
      :columns="catalogVariantsColumns"
      caption="Варианты товара"
      class="max-h-[60dvh] lg:max-h-none"
      :items="items"
      :disabled="disabled"
      :image-url="imageUrl"
      :can-quick-edit="canQuickEdit"
      @open="emit('open', $event)"
      @quick-edit="(item, section) => emit('quickEdit', item, section)"
      @remove="emit('remove', $event.id)"
    />
    <div v-else-if="!error" class="min-h-0 flex-1 overflow-auto">
      <EmptyState
        :icon="Layers"
        :title="
          outOfRange ? 'На этой странице нет вариантов' : 'Вариантов пока нет'
        "
        :description="
          outOfRange
            ? 'Перейдите на первую страницу списка вариантов.'
            : 'Добавьте первую продаваемую позицию товара.'
        "
        :primary-action-label="
          outOfRange ? 'На первую страницу' : 'Добавить вариант'
        "
        :primary-disabled="!outOfRange && !canCreate"
        @primary-action="outOfRange ? emit('firstPage') : emit('create')"
      />
    </div>
  </div>
</template>
