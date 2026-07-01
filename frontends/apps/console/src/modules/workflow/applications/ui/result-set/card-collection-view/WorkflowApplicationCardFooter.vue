<script setup lang="ts">
import { computed } from "vue";
import { Pencil } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import { CardFooter } from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";

const props = defineProps<{
  application: WorkflowApplicationListItem;
}>();

const emit = defineEmits<{
  (event: "edit", value: WorkflowApplicationListItem): void;
}>();

const createdAtLabel = computed(() => {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(props.application.createdAt));
});
</script>

<template>
  <CardFooter class="justify-between gap-3 text-xs text-muted-foreground">
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      aria-label="Edit workflow application"
      @click="emit('edit', application)"
    >
      <Pencil data-icon="inline-start" />
      <span class="sr-only">Edit</span>
    </Button>

    <dl class="grid gap-1 text-right">
      <dt class="font-medium text-foreground">Created</dt>
      <dd>
        {{ createdAtLabel }}
      </dd>
    </dl>
  </CardFooter>
</template>
