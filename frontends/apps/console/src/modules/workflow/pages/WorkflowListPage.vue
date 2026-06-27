<script setup lang="ts">
import { ref } from "vue";
import { Plus, Workflow } from "@lucide/vue";

import { Button } from "@/components/ui/button";
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
import CreateWorkflowForm from "@/modules/workflow/components/CreateWorkflowForm.vue";
import type { WorkflowApplication } from "@/modules/workflow/api";

interface WorkflowListItem {
  id: string;
  title: string;
  description: string | null;
  icon: string;
  iconBackground: string;
}

const isCreateFormOpen = ref(false);
const workflows = ref<WorkflowListItem[]>([]);

function addCreatedWorkflow(workflow: WorkflowApplication) {
  workflows.value = [
    {
      id: workflow.id,
      title: workflow.title,
      description: workflow.description,
      icon: workflow.icon,
      iconBackground: workflow.icon_background,
    },
    ...workflows.value,
  ];
}
</script>

<template>
  <section class="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden">
    <div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-start">
      <div class="grid gap-1">
        <h2 class="text-lg font-semibold tracking-normal">Workflows</h2>
        <p class="max-w-3xl text-sm text-muted-foreground">
          Created workflows will appear here as cards.
        </p>
      </div>

      <Button type="button" @click="isCreateFormOpen = true">
        <Plus data-icon="inline-start" />
        New workflow
      </Button>
    </div>

    <div
      v-if="workflows.length > 0"
      class="grid min-h-0 gap-3 overflow-auto sm:grid-cols-2 xl:grid-cols-3"
    >
      <Card
        v-for="workflow in workflows"
        :key="workflow.id"
        class="min-h-36"
      >
        <CardHeader>
          <div class="flex items-start gap-3">
            <div
              class="flex size-10 shrink-0 items-center justify-center rounded-md text-xl shadow-xs"
              :style="{ backgroundColor: workflow.iconBackground }"
              aria-hidden="true"
            >
              {{ workflow.icon }}
            </div>
            <div class="min-w-0">
              <CardTitle class="truncate text-sm">
                {{ workflow.title }}
              </CardTitle>
              <CardDescription class="truncate">
                {{ workflow.description || "Draft flow" }}
              </CardDescription>
            </div>
          </div>
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

    <CreateWorkflowForm
      v-model:open="isCreateFormOpen"
      @created="addCreatedWorkflow"
    />
  </section>
</template>
