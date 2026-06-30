<script setup lang="ts">
import { computed } from "vue";

import { Badge } from "@/components/ui/badge";
import { CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";

const props = defineProps<{
  application: WorkflowApplicationListItem;
}>();

const description = computed(() => {
  return props.application.description?.trim() || "No description";
});
</script>

<template>
  <CardHeader class="grid-cols-[auto_1fr_auto] gap-x-3 gap-y-2">
    <div
      class="row-span-2 flex size-11 items-center justify-center rounded-md border text-lg font-semibold"
      :style="{ backgroundColor: application.iconBackground }"
      aria-hidden="true"
    >
      {{ application.icon }}
    </div>

    <CardTitle class="truncate text-base">
      {{ application.title }}
    </CardTitle>

    <Badge variant="outline">
      {{ application.status }}
    </Badge>

    <CardDescription class="col-span-2 line-clamp-2">
      {{ description }}
    </CardDescription>
  </CardHeader>
</template>
