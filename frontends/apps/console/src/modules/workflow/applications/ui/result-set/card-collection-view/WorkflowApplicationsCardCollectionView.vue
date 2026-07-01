<script setup lang="ts">
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationCardView from "@/modules/workflow/applications/ui/result-set/card-collection-view/WorkflowApplicationCardView.vue";

defineProps<{
  items: WorkflowApplicationListItem[];
}>();

const emit = defineEmits<{
  (event: "edit", value: WorkflowApplicationListItem): void;
}>();
</script>

<template>
  <div
    class="grid grid-cols-[repeat(auto-fill,minmax(min(100%,22rem),1fr))] items-stretch gap-4"
  >
    <WorkflowApplicationCardView
      v-for="application in items"
      :key="application.id"
      :application="application"
      @edit="emit('edit', $event)"
    />
  </div>
</template>
