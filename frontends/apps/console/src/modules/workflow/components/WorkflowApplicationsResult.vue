<script setup lang="ts">
import type { WorkflowApplicationListItem } from "@/modules/workflow/model/workflow-application.types.ts";
import WorkflowApplicationCard from "@/modules/workflow/components/WorkflowApplicationCard.vue";

defineProps<{
  applications: WorkflowApplicationListItem[];
}>();
</script>

<template>
  <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
    <WorkflowApplicationCard
      v-for="application in applications"
      :key="application.id"
      :application="application"
    />
  </div>
</template>
