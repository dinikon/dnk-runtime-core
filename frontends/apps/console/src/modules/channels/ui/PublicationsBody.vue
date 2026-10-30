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
import PublicationsTable from "./PublicationsTable.vue";

defineProps<{
  items: PublicationCard[];
  pending: boolean;
  error: string;
  scrollKey: string;
  busy?: boolean;
  outOfRange?: boolean;
}>();
const emit = defineEmits<{
  retry: [];
  open: [id: string];
  unlink: [publicationId: string, bindingId: string];
  openCatalog: [id: string];
  firstPage: [];
  connect: [id: string];
  create: [id: string];
}>();
</script>

<template>
  <div
    class="flex min-h-60 min-w-0 flex-1 flex-col gap-3 lg:min-h-0"
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
    <div class="flex min-h-0 min-w-0 flex-1 flex-col">
      <PublicationsTable
        v-if="items.length"
        :key="scrollKey"
        :items="items"
        :busy="busy"
        @connect="emit('connect', $event)"
        @create="emit('create', $event)"
        @unlink="
          (publicationId, bindingId) => emit('unlink', publicationId, bindingId)
        "
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
          <EmptyTitle>{{
            outOfRange
              ? "На этой странице нет публикаций"
              : "Публикации не найдены"
          }}</EmptyTitle>
          <EmptyDescription
            >Запустите синхронизацию или измените поиск.</EmptyDescription
          >
        </EmptyHeader>
        <Button v-if="outOfRange" variant="outline" @click="emit('firstPage')"
          >На первую страницу</Button
        >
      </Empty>
    </div>
  </div>
</template>
