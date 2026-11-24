<script setup lang="ts">
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { FeedSection } from "../../model/feed.navigation";
defineProps<{
  current: FeedSection;
  disabled?: boolean;
}>();
const emit = defineEmits<{
  navigate: [section: FeedSection];
}>();
</script>
<template>
  <Tabs
    :model-value="current"
    @update:model-value="
      ($event === 'settings' ||
        $event === 'schema' ||
        $event === 'publications' ||
        $event === 'preview' ||
        $event === 'export') &&
      emit('navigate', $event)
    "
  >
    <TabsList
      class="h-auto max-w-full flex-wrap justify-start [&_[data-slot=tabs-trigger]]:h-8"
    >
      <TabsTrigger value="settings" :disabled="disabled">Настройки</TabsTrigger>
      <TabsTrigger value="schema" :disabled="disabled">Схема</TabsTrigger>
      <TabsTrigger value="publications" :disabled="disabled">Товары</TabsTrigger>
      <TabsTrigger value="preview" :disabled="disabled">Предпросмотр</TabsTrigger>
      <TabsTrigger value="export" :disabled="disabled">Экспорт</TabsTrigger>
    </TabsList>
  </Tabs>
</template>
