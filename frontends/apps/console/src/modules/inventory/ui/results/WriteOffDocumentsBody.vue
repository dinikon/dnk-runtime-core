<script setup lang="ts">
import { Button } from "@/components/ui/button";
import WriteOffDocumentsTable from "./WriteOffDocumentsTable.vue";
import type { WriteOffsPage } from "../../model/write-off.types";
defineProps<{
  page?: WriteOffsPage;
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
      Загрузка списаний…
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
        Списания не найдены. Создайте черновик или измените фильтры.
      </p>
      <WriteOffDocumentsTable
        v-else
        :items="page.items"
        @open="emit('open', $event)"
    /></template>
  </div>
</template>
