<script setup lang="ts">
import { Button } from "@/components/ui/button";
import type { CollectionItem } from "../model/catalog.types";
defineProps<{ items: CollectionItem[]; pending: boolean }>();
defineEmits<{ open: [item: CollectionItem]; delete: [item: CollectionItem] }>();
</script>
<template>
  <div class="overflow-hidden rounded-lg border divide-y">
    <div
      v-for="item in items"
      :key="item.id"
      class="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
    >
      <button class="min-w-0 text-left" @click="$emit('open', item)">
        <span class="font-medium">{{ item.label }}</span>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ item.description }}<span v-if="item.system"> · Системный</span>
        </p></button
      ><Button
        v-if="!item.system"
        variant="ghost"
        :disabled="pending"
        @click="$emit('delete', item)"
        >Удалить</Button
      >
    </div>
  </div>
</template>
