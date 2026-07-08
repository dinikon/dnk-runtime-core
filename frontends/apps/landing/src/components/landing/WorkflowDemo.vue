<script setup lang="ts">
import {
  Database,
  Mail,
  Radio,
  RefreshCw,
  Split,
} from "@lucide/vue";
import WorkflowNodeCard from "./WorkflowNodeCard.vue";

const demoNodes = [
  {
    title: "Trigger",
    label: "Customer event",
    metric: "0.12s",
    status: "done" as const,
    icon: Radio,
    accent: "teal" as const,
  },
  {
    title: "Segment",
    label: "Schema lookup",
    metric: "1.9k",
    status: "done" as const,
    icon: Database,
    accent: "blue" as const,
  },
  {
    title: "Decision",
    label: "Intent branch",
    metric: "3 paths",
    status: "done" as const,
    icon: Split,
    accent: "amber" as const,
  },
  {
    title: "Message",
    label: "Delivery attempt",
    metric: "sent",
    status: "running" as const,
    icon: Mail,
    accent: "teal" as const,
  },
  {
    title: "Sync",
    label: "Timeline update",
    metric: "queued",
    status: "queued" as const,
    icon: RefreshCw,
    accent: "graphite" as const,
  },
];
</script>

<template>
  <section id="workflow" class="mx-auto w-full max-w-7xl px-5 pb-14 md:px-8">
    <div class="rounded-[1.75rem] border border-border bg-white p-4 soft-panel-shadow md:p-5">
      <div class="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div>
          <h2 class="text-2xl font-semibold tracking-normal">
            Workflow execution demo
          </h2>
          <p class="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            A small path shows how an event becomes a decision, a message, and
            a CRM update.
          </p>
        </div>
        <p class="text-sm font-medium text-teal-700">Live path: event to sync</p>
      </div>

      <div class="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
        <template v-for="node in demoNodes" :key="node.title">
          <WorkflowNodeCard v-bind="node" />
        </template>
      </div>
    </div>
  </section>
</template>
