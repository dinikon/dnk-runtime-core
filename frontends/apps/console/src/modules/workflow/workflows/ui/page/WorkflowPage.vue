<script setup lang="ts">
import WorkflowCompositionRoot from "@/modules/workflow/workflows/ui/page/WorkflowCompositionRoot.vue";

defineProps<{
  id: string;
}>();
</script>

<template>
  <WorkflowCompositionRoot :workflow-application-id="id" />
</template>
