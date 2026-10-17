<script setup lang="ts">
import { RefreshCw, SearchX } from "@lucide/vue";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";

defineProps<{
  pending: boolean;
  error: boolean;
  empty: boolean;
  emptyTitle: string;
  emptyDescription: string;
}>();
defineEmits<{ retry: [] }>();
</script>

<template>
  <div v-if="pending" class="flex flex-col gap-3" role="status">
    <Skeleton v-for="item in 6" :key="item" class="h-14" />
  </div>
  <Alert v-else-if="error" variant="destructive">
    <AlertTitle>Не удалось загрузить данные</AlertTitle>
    <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
      <span>Проверьте соединение и повторите запрос.</span>
      <Button variant="outline" size="sm" @click="$emit('retry')">
        <RefreshCw data-icon="inline-start" />
        Повторить
      </Button>
    </AlertDescription>
  </Alert>
  <Empty v-else-if="empty" class="min-h-72 border">
    <EmptyHeader>
      <EmptyMedia variant="icon"><SearchX /></EmptyMedia>
      <EmptyTitle>{{ emptyTitle }}</EmptyTitle>
      <EmptyDescription>{{ emptyDescription }}</EmptyDescription>
    </EmptyHeader>
    <EmptyContent><slot name="empty-action" /></EmptyContent>
  </Empty>
  <slot v-else />
</template>
