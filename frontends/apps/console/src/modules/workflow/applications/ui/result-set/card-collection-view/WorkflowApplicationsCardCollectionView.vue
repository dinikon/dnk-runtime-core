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
  <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
    <WorkflowApplicationCardView
      v-for="application in items"
      :key="application.id"
      :application="application"
      @edit="emit('edit', $event)"
    />
  </div>
</template>
