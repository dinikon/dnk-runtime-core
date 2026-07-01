<script setup lang="ts">
import { computed } from "vue";

import { CardContent } from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";

const props = defineProps<{
  application: WorkflowApplicationListItem;
}>();

const description = computed(() => {
  return props.application.description?.trim() || "No description";
});
</script>

<template>
  <CardContent class="flex-1 px-4 pt-2 pb-4">
    <p class="line-clamp-3 text-base leading-6 font-medium text-muted-foreground">
      {{ description }}
    </p>
  </CardContent>
</template>
