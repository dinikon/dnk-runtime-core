<script setup lang="ts">
import { Workflow } from "@lucide/vue";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";

interface WorkflowListItem {
  id: string;
  title: string;
  description: string;
}

const workflows: WorkflowListItem[] = [];
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <div class="grid gap-1">
      <h2 class="text-lg font-semibold tracking-normal">Workflows</h2>
      <p class="max-w-3xl text-sm text-muted-foreground">
        Created workflows will appear here as cards.
      </p>
    </div>

    <div
      v-if="workflows.length"
      class="grid min-h-0 gap-3 overflow-auto sm:grid-cols-2 xl:grid-cols-3"
    >
      <Card
        v-for="workflow in workflows"
        :key="workflow.id"
        class="min-h-36"
      >
        <CardHeader>
          <CardTitle class="text-sm">{{ workflow.title }}</CardTitle>
          <CardDescription>{{ workflow.description }}</CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </div>

    <Empty v-else class="min-h-72 border">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Workflow aria-hidden="true" />
        </EmptyMedia>
        <EmptyTitle>No workflows yet</EmptyTitle>
        <EmptyDescription>
          The workflow list is ready for the card view.
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  </section>
</template>
