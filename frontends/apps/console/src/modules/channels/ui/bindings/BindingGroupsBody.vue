<script setup lang="ts">
import { Link2 } from "@lucide/vue";
import { EmptyState } from "@/components/custom-ui/empty-state";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { CatalogBinding } from "../../model/bindings/binding.types";
import BindingGroupsTable from "./BindingGroupsTable.vue";
defineProps<{
  items: readonly CatalogBinding[];
  loading: boolean;
  error: string;
  busy: boolean;
  canCreate: boolean;
  showCatalog: boolean;
  outOfRange: boolean;
}>();
const emit = defineEmits<{
  edit: [group: CatalogBinding];
  remove: [group: CatalogBinding];
  catalog: [id: string];
  publication: [group: CatalogBinding];
  retry: [];
  create: [];
  firstPage: [];
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
      aria-label="Загрузка публикаций"
    >
      <Skeleton class="h-10 w-full shrink-0" /><Skeleton
        v-for="index in 8"
        :key="index"
        class="h-10 w-full shrink-0"
      />
    </div>
    <BindingGroupsTable
      v-else-if="items.length"
      :items="items"
      :busy="busy"
      :show-catalog="showCatalog"
      @edit="emit('edit', $event)"
      @remove="emit('remove', $event)"
      @catalog="emit('catalog', $event)"
      @publication="emit('publication', $event)"
    />
    <div v-else-if="!error" class="min-h-0 flex-1 overflow-auto">
      <EmptyState
        :icon="Link2"
        :title="
          outOfRange
            ? 'На этой странице нет публикаций'
            : 'Связанных публикаций пока нет'
        "
        :description="
          outOfRange
            ? 'Перейдите на первую страницу списка.'
            : 'Создайте связь с публикацией канала продаж.'
        "
        :primary-action-label="
          outOfRange ? 'На первую страницу' : 'Создать связь'
        "
        :primary-disabled="!outOfRange && !canCreate"
        @primary-action="outOfRange ? emit('firstPage') : emit('create')"
      />
    </div>
  </div>
</template>
