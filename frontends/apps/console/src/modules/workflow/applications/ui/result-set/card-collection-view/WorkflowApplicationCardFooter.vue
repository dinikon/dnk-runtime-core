<script setup lang="ts">
import { Pencil } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import { CardFooter } from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";

defineProps<{
  application: WorkflowApplicationListItem;
}>();

const emit = defineEmits<{
  (event: "edit", value: WorkflowApplicationListItem): void;
}>();
</script>

<template>
  <CardFooter class="relative z-20 mt-auto justify-end px-4 pt-2 pb-4">
    <div class="flex items-center border-l pl-4">
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Edit workflow application"
        @click.stop="emit('edit', application)"
      >
        <Pencil data-icon="inline-start" />
        <span class="sr-only">Edit</span>
      </Button>
    </div>
  </CardFooter>
</template>
