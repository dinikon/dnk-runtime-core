<script setup lang="ts">
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ContentUpdateSummary } from "../model/content-update.types";
import { contentUpdateLabels } from "../model/content-update.presentation";
import { dateLabel } from "../model/channels.presentation";
defineProps<{ items: ContentUpdateSummary[] }>();
defineEmits<{ open: [id: string] }>();
</script>
<template>
  <div v-if="items.length" class="flex flex-col gap-2">
    <h2 class="text-sm font-medium">Последние обновления текстов</h2>
    <div
      v-for="item in items"
      :key="item.id"
      class="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3"
    >
      <div class="flex flex-wrap items-center gap-3">
        <Badge variant="outline">{{
          contentUpdateLabels[item.status] ?? item.status
        }}</Badge>
        <span class="text-muted-foreground text-sm"
          >{{ dateLabel(item.createdAt) }} · Публикаций: {{ item.total }}</span
        >
      </div>
      <Button variant="ghost" size="sm" @click="$emit('open', item.id)"
        >Открыть результат</Button
      >
    </div>
  </div>
</template>
