<script setup lang="ts">
import { Badge } from "@/components/ui/badge";
import { CardContent } from "@/components/ui/card";
import type { WorkflowApplicationListItem } from "@/modules/workflow/applications/model/workflow-application.types.ts";

defineProps<{
  application: WorkflowApplicationListItem;
}>();
</script>

<template>
  <CardContent class="flex flex-col gap-3">
    <div class="flex flex-wrap gap-2">
      <Badge variant="secondary">
        {{ application.kind }}
      </Badge>
    </div>

    <dl class="grid gap-2 text-xs text-muted-foreground">
      <div class="grid gap-1">
        <dt class="font-medium text-foreground">ID</dt>
        <dd class="truncate">
          {{ application.id }}
        </dd>
      </div>
    </dl>
  </CardContent>
</template>
