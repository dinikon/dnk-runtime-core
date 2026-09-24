<script setup lang="ts">
import { RefreshCw, Users } from "@lucide/vue";

import { Alert, AlertDescription } from "@/components/ui/alert";
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
defineEmits<{
  retry: [];
}>();
</script>

<template>
  <div v-if="pending" class="grid gap-2" role="status">
    <Skeleton v-for="item in 4" :key="item" class="h-16 rounded-lg" />
    <span class="sr-only">Загрузка данных…</span>
  </div>
  <Alert v-else-if="error" variant="destructive">
    <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
      <span>Не удалось загрузить данные. Повторите попытку.</span>
      <Button size="sm" variant="outline" @click="$emit('retry')">
        <RefreshCw />
        Повторить
      </Button>
    </AlertDescription>
  </Alert>
  <Empty v-else-if="empty" class="min-h-56 rounded-lg border">
    <EmptyHeader>
      <EmptyMedia variant="icon"><Users /></EmptyMedia>
      <EmptyTitle>{{ emptyTitle }}</EmptyTitle>
      <EmptyDescription>{{ emptyDescription }}</EmptyDescription>
    </EmptyHeader>
    <EmptyContent><slot name="empty-action" /></EmptyContent>
  </Empty>
  <slot v-else />
</template>
