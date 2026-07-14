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
  (event: "open", value: WorkflowApplicationListItem): void;
  (event: "edit", value: WorkflowApplicationListItem): void;
}>();
</script>

<template>
  <Card
    class="group relative isolate h-full min-h-32 gap-0 overflow-hidden rounded-2xl py-0"
  >
    <button
      type="button"
      class="absolute inset-0 z-0 cursor-pointer rounded-2xl transition-colors hover:bg-accent/30 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset focus-visible:outline-none"
      :aria-label="`Open ${application.title} workflow editor`"
      @click="emit('open', application)"
    >
      <span class="sr-only">Open {{ application.title }} workflow editor</span>
    </button>

    <div class="pointer-events-none relative z-10 flex flex-1 flex-col">
      <WorkflowApplicationCardHeader :application="application" />
      <WorkflowApplicationCardContent :application="application" />
    </div>

    <WorkflowApplicationCardFooter
      :application="application"
      @edit="emit('edit', $event)"
    />
  </Card>
</template>
