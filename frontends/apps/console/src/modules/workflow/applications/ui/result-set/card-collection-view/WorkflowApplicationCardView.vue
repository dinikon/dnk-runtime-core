<script setup lang="ts">
import { Card } from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";
import WorkflowApplicationCardContent from "@/modules/workflow/applications/ui/result-set/card-collection-view/WorkflowApplicationCardContent.vue";
import WorkflowApplicationCardFooter from "@/modules/workflow/applications/ui/result-set/card-collection-view/WorkflowApplicationCardFooter.vue";
import WorkflowApplicationCardHeader from "@/modules/workflow/applications/ui/result-set/card-collection-view/WorkflowApplicationCardHeader.vue";

defineProps<{
  application: WorkflowApplicationListItem;
}>();

const emit = defineEmits<{
  (event: "edit", value: WorkflowApplicationListItem): void;
}>();
</script>

<template>
  <Card class="h-full min-h-32 gap-0 overflow-hidden rounded-2xl py-0">
    <WorkflowApplicationCardHeader :application="application" />
    <WorkflowApplicationCardContent :application="application" />
    <WorkflowApplicationCardFooter
      :application="application"
      @edit="emit('edit', $event)"
    />
  </Card>
</template>
