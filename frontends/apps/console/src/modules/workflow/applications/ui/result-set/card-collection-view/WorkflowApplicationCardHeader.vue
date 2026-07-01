<script setup lang="ts">
import { computed } from "vue";

import { CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";

const props = defineProps<{
  application: WorkflowApplicationListItem;
}>();

const editedAtLabel = computed(() => {
  return new Intl.DateTimeFormat("en-US", {
    day: "2-digit",
    hour: "2-digit",
    hour12: false,
    minute: "2-digit",
    month: "2-digit",
    year: "numeric",
  })
    .format(new Date(props.application.createdAt))
    .replace(",", "");
});
</script>

<template>
  <CardHeader class="grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-2 p-4 pb-2">
    <div
      class="row-span-2 flex size-14 items-center justify-center rounded-2xl border text-2xl shadow-xs"
      :style="{ backgroundColor: application.iconBackground }"
      aria-hidden="true"
    >
      {{ application.icon }}
    </div>

    <CardTitle class="min-w-0 truncate text-[16px] leading-6 font-semibold">
      {{ application.title }}
    </CardTitle>

    <CardDescription class="min-w-0 truncate text-[12px] leading-5 font-medium">
      {{ application.kind }} · Edited at {{ editedAtLabel }}
    </CardDescription>
  </CardHeader>
</template>
