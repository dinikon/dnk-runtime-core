<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  Database,
  Mail,
  Pause,
  Play,
  Radio,
  RefreshCw,
  Split,
  Workflow,
} from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import WorkflowNodeCard from "./WorkflowNodeCard.vue";

type NodeStatus = "queued" | "running" | "done";
type NodeAccent = "teal" | "amber" | "blue" | "graphite";

const nodes = [
  {
    title: "Trigger",
    label: "Event",
    metric: "0.12s",
    icon: Radio,
    accent: "teal" as NodeAccent,
  },
  {
    title: "Segment",
    label: "Schema lookup",
    metric: "1.9k",
    icon: Database,
    accent: "blue" as NodeAccent,
  },
  {
    title: "Decision",
    label: "Intent branch",
    metric: "3 paths",
    icon: Split,
    accent: "amber" as NodeAccent,
  },
  {
    title: "Message",
    label: "Delivery",
    metric: "sent",
    icon: Mail,
    accent: "teal" as NodeAccent,
  },
  {
    title: "Sync",
    label: "CRM sync",
    metric: "done",
    icon: RefreshCw,
    accent: "graphite" as NodeAccent,
  },
];

const activeIndex = ref(2);
const isRunning = ref(true);
let timer: number | undefined;

const currentNode = computed(() => nodes[activeIndex.value]);
const progressPercent = computed(() =>
  Math.round(((activeIndex.value + 1) / nodes.length) * 100),
);

const events = computed(() => [
  {
    time: "12:04:21",
    text: `${currentNode.value.title} entered execution`,
  },
  {
    time: "12:04:22",
    text: "Tenant schema resolved for dnk runtime",
  },
  {
    time: "12:04:23",
    text: "Outbox checkpoint written",
  },
]);

function statusFor(index: number): NodeStatus {
  if (index < activeIndex.value) {
    return "done";
  }

  if (index === activeIndex.value) {
    return "running";
  }

  return "queued";
}

function nextStep() {
  activeIndex.value = (activeIndex.value + 1) % nodes.length;
}

function toggleDemo() {
  isRunning.value = !isRunning.value;
}

function startTimer() {
  timer = window.setInterval(() => {
    if (isRunning.value) {
      nextStep();
    }
  }, 2200);
}

onMounted(startTimer);

onBeforeUnmount(() => {
  if (timer !== undefined) {
    window.clearInterval(timer);
  }
});
</script>

<template>
  <div class="workflow-grid relative min-h-[560px] overflow-hidden rounded-[1.75rem] border border-border bg-white soft-panel-shadow">
    <div class="absolute inset-x-0 top-0 flex items-center justify-between gap-4 border-b border-border bg-white/82 px-5 py-4 backdrop-blur">
      <div class="flex min-w-0 items-center gap-3">
        <div class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Workflow class="size-4" aria-hidden="true" />
        </div>
        <div class="min-w-0">
          <p class="truncate text-sm font-semibold leading-5">Tenant lifecycle workflow</p>
          <p class="truncate text-xs text-muted-foreground">
            acme.dniko.app / execution #2384
          </p>
        </div>
      </div>

      <Button
        variant="outline"
        size="sm"
        class="hidden bg-white/90 sm:inline-flex"
        type="button"
        @click="toggleDemo"
      >
        <Pause v-if="isRunning" data-icon="inline-start" aria-hidden="true" />
        <Play v-else data-icon="inline-start" aria-hidden="true" />
        {{ isRunning ? "Pause demo" : "Run demo" }}
      </Button>
    </div>

    <svg
      class="pointer-events-none absolute inset-0 mt-16 hidden h-full w-full md:block"
      viewBox="0 0 760 500"
      fill="none"
      aria-hidden="true"
    >
      <path
        class="map-line-dash"
        d="M91 150 C185 76 260 92 328 165 S475 292 648 196"
        stroke="oklch(0.62 0.12 194)"
        stroke-width="2"
      />
      <path
        d="M117 326 C220 260 312 278 383 345 S516 410 661 306"
        stroke="oklch(0.72 0.12 78)"
        stroke-width="2"
        stroke-dasharray="5 8"
      />
      <circle cx="91" cy="150" r="5" fill="oklch(0.62 0.12 194)" />
      <circle cx="328" cy="165" r="5" fill="oklch(0.62 0.12 194)" />
      <circle cx="648" cy="196" r="5" fill="oklch(0.62 0.12 194)" />
    </svg>

    <div class="absolute left-5 right-5 top-24 hidden md:block">
      <div class="relative min-h-[360px]">
        <div class="absolute left-0 top-16 w-[210px]">
          <WorkflowNodeCard v-bind="nodes[0]" :status="statusFor(0)" compact />
        </div>
        <div class="absolute left-[30%] top-0 w-[230px]">
          <WorkflowNodeCard v-bind="nodes[1]" :status="statusFor(1)" compact />
        </div>
        <div class="absolute left-[43%] top-48 w-[230px]">
          <WorkflowNodeCard v-bind="nodes[2]" :status="statusFor(2)" compact />
        </div>
        <div class="absolute right-0 top-24 w-[220px]">
          <WorkflowNodeCard v-bind="nodes[3]" :status="statusFor(3)" compact />
        </div>
        <div class="absolute bottom-0 left-[12%] w-[220px]">
          <WorkflowNodeCard v-bind="nodes[4]" :status="statusFor(4)" compact />
        </div>
      </div>
    </div>

    <div class="grid gap-3 px-4 pt-24 md:hidden">
      <WorkflowNodeCard
        v-for="(node, index) in nodes"
        :key="node.title"
        v-bind="node"
        :status="statusFor(index)"
        compact
      />
    </div>

    <Card class="absolute bottom-5 left-5 right-5 gap-4 rounded-2xl border-border/90 bg-white/92 py-4 backdrop-blur md:left-auto md:w-[330px]">
      <CardHeader class="px-4">
        <div class="flex items-center justify-between gap-3">
          <CardTitle class="text-sm">Execution inspector</CardTitle>
          <Badge variant="warning">{{ progressPercent }}%</Badge>
        </div>
      </CardHeader>
      <CardContent class="grid gap-3 px-4">
        <div class="flex items-center justify-between rounded-lg bg-muted/70 px-3 py-2">
          <span class="text-xs font-medium text-muted-foreground">Active node</span>
          <span class="text-xs font-semibold">{{ currentNode.title }}</span>
        </div>
        <div class="grid gap-2">
          <div
            v-for="event in events"
            :key="`${event.time}-${event.text}`"
            class="flex items-start gap-2 text-xs"
          >
            <span class="mt-0.5 size-1.5 shrink-0 rounded-full bg-teal-500" />
            <span class="shrink-0 font-medium text-muted-foreground">{{ event.time }}</span>
            <span class="min-w-0 text-foreground">{{ event.text }}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>

</template>
