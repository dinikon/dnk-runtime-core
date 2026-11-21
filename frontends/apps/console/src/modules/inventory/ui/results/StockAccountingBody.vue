<script setup lang="ts">
import { Button } from "@/components/ui/button";
withDefaults(
  defineProps<{
    loading: boolean;
    error: string;
    hasData: boolean;
    empty: boolean;
    canRetry: boolean;
    fetching: boolean;
    loadingText?: string;
    emptyText?: string;
  }>(),
  {
    loadingText: "Загрузка учёта…",
    emptyText: "По выбранным условиям записей нет.",
  },
);
const emit = defineEmits<{ retry: [] }>();
</script>
<template>
  <div class="flex min-w-0 shrink-0 flex-col gap-4">
    <div
      v-if="error"
      role="alert"
      class="rounded-md border border-destructive p-3 text-sm text-destructive"
    >
      {{ error
      }}<Button variant="outline" :disabled="!canRetry" @click="emit('retry')"
        >Повторить</Button
      >
    </div>
    <p v-if="loading" role="status">{{ loadingText }}</p>
    <p
      v-else-if="fetching && hasData"
      role="status"
      class="text-xs text-muted-foreground"
    >
      Обновление данных…
    </p>
    <template v-if="hasData"
      ><p
        v-if="empty"
        class="rounded-md border p-6 text-sm text-muted-foreground"
      >
        {{ emptyText }}
      </p>
      <slot v-else /><slot name="footer"
    /></template>
  </div>
</template>
