<script setup lang="ts">
import { computed } from "vue";

import { CardFooter } from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";

const props = defineProps<{
  application: WorkflowApplicationListItem;
}>();

const createdAtLabel = computed(() => {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(props.application.createdAt));
});
</script>

<template>
  <CardFooter class="text-xs text-muted-foreground">
    <dl class="grid gap-1">
      <dt class="font-medium text-foreground">Created</dt>
      <dd>
        {{ createdAtLabel }}
      </dd>
    </dl>
  </CardFooter>
</template>
