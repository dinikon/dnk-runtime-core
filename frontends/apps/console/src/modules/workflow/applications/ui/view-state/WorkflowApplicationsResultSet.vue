<script setup lang="ts">
import type { WorkflowApplicationsViewMode } from "@/modules/workflow/applications/model/use-workflow-applications-page-state.ts";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationsCardCollectionView from "@/modules/workflow/applications/ui/result-set/card-collection-view/WorkflowApplicationsCardCollectionView.vue";

defineProps<{
  items: WorkflowApplicationListItem[];
  viewMode: WorkflowApplicationsViewMode;
}>();

const emit = defineEmits<{
  (event: "edit", value: WorkflowApplicationListItem): void;
}>();
</script>

<template>
  <WorkflowApplicationsCardCollectionView
    v-if="viewMode === 'cards'"
    :items="items"
    @edit="emit('edit', $event)"
  />
</template>
