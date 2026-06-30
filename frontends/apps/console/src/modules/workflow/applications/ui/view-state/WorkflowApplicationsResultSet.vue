<script setup lang="ts">
import type { WorkflowApplicationsViewMode } from "@/modules/workflow/applications/model/use-workflow-applications-page-state.ts";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationsCardCollectionView from "@/modules/workflow/applications/ui/result-set/card-collection-view/WorkflowApplicationsCardCollectionView.vue";

defineProps<{
  items: WorkflowApplicationListItem[];
  viewMode: WorkflowApplicationsViewMode;
}>();
</script>

<template>
  <WorkflowApplicationsCardCollectionView
    v-if="viewMode === 'cards'"
    :items="items"
  />
</template>
