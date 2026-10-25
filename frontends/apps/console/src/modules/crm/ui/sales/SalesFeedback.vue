<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyHeader,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty";
defineProps<{
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
}>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div v-if="loading" class="flex flex-col gap-3" aria-label="Загрузка">
    <Skeleton class="h-24 w-full" /><Skeleton class="h-24 w-full" />
  </div>
  <Alert v-else-if="error" variant="destructive"
    ><AlertDescription class="flex flex-wrap items-center gap-3"
      >{{ error
      }}<Button variant="outline" @click="$emit('retry')"
        >Повторить</Button
      ></AlertDescription
    ></Alert
  ><Empty v-else-if="empty"
    ><EmptyHeader
      ><EmptyTitle>{{ emptyTitle ?? "Ничего не найдено" }}</EmptyTitle
      ><EmptyDescription>{{
        emptyDescription ?? "Измените фильтры или создайте новую запись."
      }}</EmptyDescription></EmptyHeader
    ><slot name="empty-action" /></Empty
  ><slot v-else />
</template>
