<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import type { PublicationCard } from "../model/publication.types";
import type { PublicationCreationState } from "../model/catalog-creation.types";
import PublicationsTable from "./PublicationsTable.vue";

defineProps<{
  items: PublicationCard[];
  pending: boolean;
  error: string;
  scrollKey: string;
  creation?: Record<string, PublicationCreationState>;
}>();
const emit = defineEmits<{
  retry: [];
  open: [id: string];
  create: [id: string];
  openCatalog: [id: string];
}>();
</script>

<template>
  <div
    class="flex min-h-60 min-w-0 flex-1 flex-col gap-3"
    :aria-busy="pending"
    data-slot="publications-body"
  >
    <Alert v-if="error" variant="destructive" class="shrink-0">
      <AlertDescription
        class="flex flex-wrap items-center justify-between gap-3"
      >
        {{ error }}
        <Button variant="outline" size="sm" @click="emit('retry')"
          >Повторить</Button
        >
      </AlertDescription>
    </Alert>
    <div class="min-h-0 flex-1 [&>[data-slot=table-container]]:h-full">
      <PublicationsTable
        v-if="items.length"
        :key="scrollKey"
        :items="items"
        :creation="creation"
        @create="emit('create', $event)"
        @open-catalog="emit('openCatalog', $event)"
        @open="emit('open', $event)"
      />
      <div
        v-else-if="pending"
        class="flex h-full flex-col gap-2"
        aria-label="Загрузка публикаций"
      >
        <Skeleton class="h-10 w-full shrink-0" />
        <Skeleton v-for="row in 3" :key="row" class="h-16 w-full shrink-0" />
      </div>
      <Empty v-else-if="!error" class="h-full border-0">
        <EmptyHeader>
          <EmptyTitle>Публикации не найдены</EmptyTitle>
          <EmptyDescription
            >Запустите синхронизацию или измените поиск.</EmptyDescription
          >
        </EmptyHeader>
      </Empty>
    </div>
  </div>
</template>
