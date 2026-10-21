<script setup lang="ts">
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { BatchExportItem } from "../model/batch-export.types";
import {
  exportItemLabels,
  exportReason,
} from "../model/batch-export.presentation";
defineProps<{ items: BatchExportItem[] }>();
defineEmits<{ catalog: [item: BatchExportItem] }>();
</script>
<template>
  <div class="flex flex-col gap-3">
    <article
      v-for="item in items"
      :key="item.publicationId"
      class="flex flex-col gap-3 rounded-md border p-4 sm:flex-row sm:justify-between"
    >
      <div class="flex min-w-0 flex-col gap-2">
        <span class="font-medium break-words">{{
          Object.values(item.titles)[0] ?? `Публикация ${item.externalId}`
        }}</span
        ><span class="text-muted-foreground text-xs"
          >ID: {{ item.externalId }}</span
        ><Badge class="w-fit" variant="outline">{{
          exportItemLabels[item.status] ?? "Не подтверждено"
        }}</Badge>
        <p
          v-for="issue in item.issues"
          :key="issue"
          class="text-muted-foreground text-sm"
        >
          {{ exportReason(issue) }}
        </p>
      </div>
      <Button
        class="shrink-0"
        variant="outline"
        size="sm"
        @click="$emit('catalog', item)"
        >Товар каталога</Button
      >
    </article>
  </div>
</template>
