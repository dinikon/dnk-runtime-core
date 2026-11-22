<script setup lang="ts">
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
defineProps<{
  current: "settings" | "schema" | "publications";
  disabled?: boolean;
}>();
const emit = defineEmits<{
  navigate: [section: "settings" | "schema" | "publications"];
}>();
</script>
<template>
  <Tabs
    :model-value="current"
    @update:model-value="
      ($event === 'settings' ||
        $event === 'schema' ||
        $event === 'publications') &&
      emit('navigate', $event)
    "
    ><TabsList
      ><TabsTrigger value="settings" :disabled="disabled">Настройки</TabsTrigger
      ><TabsTrigger value="schema" :disabled="disabled">Схема</TabsTrigger
      ><TabsTrigger value="publications" :disabled="disabled"
        >Товары</TabsTrigger
      ></TabsList
    ></Tabs
  >
</template>
