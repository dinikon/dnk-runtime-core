<script setup lang="ts">
import {
  PageHeader,
  PageHeaderActions,
  PageHeaderTabs,
  type PageHeaderAction,
} from "@/components/custom-ui/page-header";

defineProps<{
  title: string;
  description?: string;
  activeTab: "settings" | "publications";
  actions: readonly PageHeaderAction[];
}>();
const emit = defineEmits<{
  tab: [value: "settings" | "publications"];
  action: [id: string];
}>();
const tabs = [
  { value: "settings", label: "Настройки" },
  { value: "publications", label: "Публикации" },
];
function selectTab(value: string): void {
  if (value === "settings" || value === "publications") emit("tab", value);
}
</script>

<template>
  <PageHeader :title="title" :description="description">
    <template #before>
      <PageHeaderTabs
        :model-value="activeTab"
        :items="tabs"
        aria-label="Разделы канала"
        @update:model-value="selectTab"
      />
    </template>
    <template #actions>
      <PageHeaderActions
        :actions="actions"
        @action="emit('action', $event.id)"
      />
    </template>
  </PageHeader>
</template>
