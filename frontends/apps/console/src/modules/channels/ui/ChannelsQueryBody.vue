<script setup lang="ts">
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
defineProps<{
  pending: boolean;
  error: string | null;
  hasData: boolean;
  empty: boolean;
  emptyTitle: string;
  emptyDescription: string;
}>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div class="flex min-w-0 flex-col gap-4" :aria-busy="pending">
    <Alert v-if="error" variant="destructive"
      ><AlertTitle>Не удалось обновить данные</AlertTitle
      ><AlertDescription
        >{{ error
        }}<Button variant="outline" size="sm" @click="$emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <div
      v-if="pending && !hasData"
      class="flex flex-col gap-3"
      aria-label="Загрузка"
    >
      <Skeleton v-for="n in 4" :key="n" class="h-16 w-full" />
    </div>
    <Empty v-else-if="hasData && empty"
      ><EmptyHeader
        ><EmptyTitle>{{ emptyTitle }}</EmptyTitle
        ><EmptyDescription>{{
          emptyDescription
        }}</EmptyDescription></EmptyHeader
      ><slot name="empty-action"
    /></Empty>
    <slot v-else-if="hasData" />
  </div>
</template>
