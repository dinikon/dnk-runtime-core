<script setup lang="ts">
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { SupplierSource } from "../../model/supplier-source.types";
import SupplierSourcesTable from "./SupplierSourcesTable.vue";
defineProps<{
  items: readonly SupplierSource[];
  loading: boolean;
  refreshing: boolean;
  error: string;
  canRetry: boolean;
  filtered: boolean;
  outOfRange: boolean;
}>();
const emit = defineEmits<{
  retry: [];
  clear: [];
  first: [];
  open: [id: string];
}>();
</script>
<template>
  <div class="flex min-w-0 flex-col gap-3" :aria-busy="loading || refreshing">
    <Alert v-if="error" variant="destructive"
      ><AlertDescription
        class="flex flex-wrap items-center justify-between gap-2"
        ><span>{{ error }}</span
        ><Button
          v-if="canRetry"
          variant="outline"
          size="sm"
          :disabled="refreshing"
          @click="emit('retry')"
          >Повторить</Button
        ></AlertDescription
      ></Alert
    >
    <p
      v-if="refreshing && items.length"
      role="status"
      class="text-sm text-muted-foreground"
    >
      Обновление источников…
    </p>
    <SupplierSourcesTable
      v-if="items.length"
      :items="items"
      @open="emit('open', $event)"
    />
    <div
      v-else-if="loading"
      role="status"
      aria-label="Загрузка источников"
      class="flex flex-col gap-2"
    >
      <Skeleton v-for="n in 5" :key="n" class="h-12 w-full" />
    </div>
    <div
      v-else-if="!error"
      class="flex flex-col items-center gap-3 rounded-lg border border-dashed p-8 text-center"
    >
      <p>
        {{
          outOfRange
            ? "На этой странице нет источников."
            : filtered
              ? "Ничего не найдено."
              : "Источников пока нет. Создайте первый источник поставщика."
        }}
      </p>
      <Button v-if="outOfRange" variant="outline" @click="emit('first')"
        >На первую страницу</Button
      ><Button v-else-if="filtered" variant="outline" @click="emit('clear')"
        >Сбросить фильтры</Button
      >
    </div>
  </div>
</template>
