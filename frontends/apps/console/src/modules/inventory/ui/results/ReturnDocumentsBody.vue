<script setup lang="ts">
import { Button } from "@/components/ui/button";
import ReturnDocumentsTable from "./ReturnDocumentsTable.vue";
import type { ReturnsPage } from "../../model/return.types";
defineProps<{
  page?: ReturnsPage;
  loading: boolean;
  refreshing: boolean;
  error: string;
  ready: boolean;
}>();
const emit = defineEmits<{ open: [id: string]; retry: [] }>();
</script>
<template>
  <div class="min-w-0">
    <div
      v-if="error"
      role="alert"
      class="mb-3 rounded-md border border-destructive p-3 text-sm text-destructive"
    >
      {{ error }}
      <Button
        variant="outline"
        size="sm"
        :disabled="!ready || refreshing"
        @click="emit('retry')"
        >Повторить</Button
      >
    </div>
    <p v-if="loading && !page" role="status" class="py-8 text-muted-foreground">
      Загрузка возвратов…
    </p>
    <template v-if="page && ready"
      ><p
        v-if="refreshing"
        role="status"
        class="mb-2 text-xs text-muted-foreground"
      >
        Обновление…
      </p>
      <p
        v-if="!page.items.length"
        class="rounded-md border p-6 text-muted-foreground"
      >
        Возвраты не найдены. Создайте черновик или измените фильтры.
      </p>
      <ReturnDocumentsTable
        v-else
        :items="page.items"
        @open="emit('open', $event)"
    /></template>
  </div>
</template>
