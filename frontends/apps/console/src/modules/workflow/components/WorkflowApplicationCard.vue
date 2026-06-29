<script setup lang="ts">
import { computed } from "vue";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/model/workflow-application.types.ts";

const props = defineProps<{
  application: WorkflowApplicationListItem;
}>();

const createdAtLabel = computed(() => {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(props.application.createdAt));
});

const description = computed(() => {
  return props.application.description?.trim() || "No description";
});
</script>

<template>
  <Card class="h-full gap-4 overflow-hidden">
    <CardHeader class="grid-cols-[auto_1fr] gap-x-3 gap-y-2">
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

      <CardDescription class="line-clamp-2">
        {{ description }}
      </CardDescription>
    </CardHeader>

    <CardContent class="flex flex-col gap-3">
      <div class="flex flex-wrap gap-2">
        <Badge variant="secondary">
          {{ application.kind }}
        </Badge>
        <Badge variant="outline">
          {{ application.status }}
        </Badge>
      </div>

      <dl class="grid gap-2 text-xs text-muted-foreground">
        <div class="grid gap-1">
          <dt class="font-medium text-foreground">ID</dt>
          <dd class="truncate">
            {{ application.id }}
          </dd>
        </div>

        <div class="grid gap-1">
          <dt class="font-medium text-foreground">Created</dt>
          <dd>
            {{ createdAtLabel }}
          </dd>
        </div>
      </dl>
    </CardContent>
  </Card>
</template>
