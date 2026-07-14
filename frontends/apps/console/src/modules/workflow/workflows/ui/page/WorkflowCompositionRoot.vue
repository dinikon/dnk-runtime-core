<script setup lang="ts">
import WorkflowPageLayout from "@/modules/workflow/workflows/ui/page/WorkflowPageLayout.vue";

defineProps<{
  workflowApplicationId: string;
}>();
</script>

<template>
  <WorkflowPageLayout
    :data-workflow-application-id="workflowApplicationId"
  />
</template>
