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
        $event === 'preview') &&
      emit('navigate', $event)
    "
    ><TabsList
      ><TabsTrigger value="settings" :disabled="disabled">Настройки</TabsTrigger
      ><TabsTrigger value="schema" :disabled="disabled">Схема</TabsTrigger
      ><TabsTrigger value="publications" :disabled="disabled"
        >Товары</TabsTrigger
      ><TabsTrigger value="preview" :disabled="disabled"
        >Предпросмотр</TabsTrigger
      ></TabsList
    ></Tabs
  >
</template>
