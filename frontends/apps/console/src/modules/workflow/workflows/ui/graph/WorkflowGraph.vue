<script setup lang="ts">
import WorkflowGraphCanvas from "@/modules/workflow/workflows/ui/graph/WorkflowGraphCanvas.vue";
</script>

<template>
  <section
    class="h-full min-h-0 w-full overflow-hidden"
    aria-label="Workflow editor canvas"
  >
    <WorkflowGraphCanvas />
  </section>
</template>
