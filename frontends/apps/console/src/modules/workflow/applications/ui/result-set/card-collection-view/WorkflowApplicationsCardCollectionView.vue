<script setup lang="ts">
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationCardView from "@/modules/workflow/applications/ui/result-set/card-collection-view/WorkflowApplicationCardView.vue";

defineProps<{
  items: WorkflowApplicationListItem[];
}>();
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
    <WorkflowApplicationCardView
      v-for="application in items"
      :key="application.id"
      :application="application"
    />
  </div>
</template>
