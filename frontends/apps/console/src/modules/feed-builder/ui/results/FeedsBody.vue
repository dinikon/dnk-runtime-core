<script setup lang="ts">
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import EmptyState from "@/components/custom-ui/empty-state/EmptyState.vue";
import FeedsTable from "./FeedsTable.vue";
import type { FeedListItem } from "../../model/feed.types";
defineProps<{
  loading: boolean;
  error: string;
  items: FeedListItem[];
  filtered: boolean;
  busy: boolean;
}>();
defineEmits<{
  retry: [];
  create: [];
  reset: [];
  open: [id: string];
  archive: [feed: FeedListItem];
}>();
</script>
<template>
  <div class="flex min-h-0 min-w-0 flex-1 flex-col gap-3" :aria-busy="loading">
    <Alert v-if="error" variant="destructive" class="shrink-0"
      ><AlertDescription
        class="flex flex-wrap items-center justify-between gap-3"
        >{{ error
        }}<Button variant="outline" @click="$emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <FeedsTable
      v-if="items.length"
      :items="items"
      :busy="busy"
      @open="$emit('open', $event)"
      @archive="$emit('archive', $event)"
    />
    <div
      v-else-if="loading && !error"
      role="status"
      aria-label="Загрузка фидов"
      class="flex flex-col gap-2"
    >
      <Skeleton v-for="row in 6" :key="row" class="h-10 w-full" />
    </div>
    <EmptyState
      v-else-if="!error"
      :title="filtered ? 'Фиды не найдены' : 'Фидов пока нет'"
      :description="
        filtered
          ? 'Измените поиск или сбросьте фильтры.'
          : 'Создайте фид и настройте формат выгрузки.'
      "
      :primary-action-label="filtered ? 'Сбросить фильтры' : 'Создать фид'"
      @primary-action="filtered ? $emit('reset') : $emit('create')"
    />
  </div>
</template>
