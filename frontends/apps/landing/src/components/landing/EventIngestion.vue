<script setup lang="ts">
import type { Component } from "vue";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  ChartNoAxesCombined,
  Flame,
  Goal,
  Rows3,
  Satellite,
  ShieldCheck,
  Workflow,
} from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

type StageStatus = "queued" | "running" | "done";

type EventSource = {
  name: string;
  description: string;
  batch: string;
  events: string[];
  icon: Component;
};

type PipelineStage = {
  title: string;
  description: string;
  metric: string;
  icon: Component;
};

const sources: EventSource[] = [
  {
    name: "Firebase",
    description: "Mobile and web product telemetry lands in tenant-scoped batches.",
    batch: "4.8k/min",
    events: ["app_open", "add_to_cart", "purchase", "trial_started"],
    icon: Flame,
  },
  {
    name: "AppsFlyer",
    description: "Attribution, install, revenue, and retargeting events join the same stream.",
    batch: "1.6k/min",
    events: ["install", "re-engagement", "ad_revenue", "uninstall"],
    icon: Satellite,
  },
];

const stages: PipelineStage[] = [
  {
    title: "Batch landing",
    description: "Normalize source payloads and split them by tenant.",
    metric: "6.4k/min",
    icon: Rows3,
  },
  {
    title: "Identity merge",
    description: "Attach customer, device, consent, and CRM profile records.",
    metric: "99.96%",
    icon: ShieldCheck,
  },
  {
    title: "Goal classifier",
    description: "Classify events as reached goals, partial progress, or next best action.",
    metric: "12 goals",
    icon: Goal,
  },
  {
    title: "Workflow enqueue",
    description: "Turn batches into communication chains and measurable state changes.",
    metric: "312 chains",
    icon: Workflow,
  },
];

const stats = [
  {
    label: "Goals reached",
    value: "31.8%",
    detail: "+6.4% from targeted journeys",
  },
  {
    label: "Chains created",
    value: "12,480",
    detail: "from Firebase and AppsFlyer batches",
  },
  {
    label: "Attribution windows",
    value: "7 days",
    detail: "kept per tenant and campaign",
  },
];

const activeStageIndex = ref(0);
let timer: number | undefined;

const activeStage = computed(() => stages[activeStageIndex.value] ?? stages[0]);

function stageStatus(index: number): StageStatus {
  if (index < activeStageIndex.value) {
    return "done";
  }

  if (index === activeStageIndex.value) {
    return "running";
  }

  return "queued";
}

onMounted(() => {
  timer = window.setInterval(() => {
    activeStageIndex.value = (activeStageIndex.value + 1) % stages.length;
  }, 2100);
});

onBeforeUnmount(() => {
  if (timer !== undefined) {
    window.clearInterval(timer);
  }
});
</script>

<template>
  <section id="events" class="mx-auto w-full max-w-7xl px-5 py-16 md:px-8">
    <div class="mb-8 grid gap-5 lg:grid-cols-[0.92fr_1.08fr] lg:items-end">
      <div>
        <h2 class="text-balance text-3xl font-semibold leading-tight sm:text-4xl">
          Batch events become CRM actions and goal statistics.
        </h2>
        <p class="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
          Firebase and AppsFlyer can send noisy telemetry in batches. DNK turns
          that stream into clean workflow triggers, communication chains, and
          measurable goal progress.
        </p>
      </div>
      <div class="rounded-2xl border border-border bg-white p-4">
        <div class="flex items-center justify-between gap-4">
          <div>
            <p class="text-sm font-semibold">Active transform</p>
            <p class="mt-1 text-xs text-muted-foreground">{{ activeStage.description }}</p>
          </div>
          <Badge variant="warning">{{ activeStage.title }}</Badge>
        </div>
      </div>
    </div>

    <div class="grid gap-5 lg:grid-cols-[0.82fr_1.18fr]">
      <div class="grid gap-4">
        <Card v-for="source in sources" :key="source.name" class="rounded-2xl py-5">
          <CardHeader class="px-5">
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-center gap-3">
                <div class="flex size-10 items-center justify-center rounded-lg border border-border bg-secondary">
                  <component :is="source.icon" class="size-4" aria-hidden="true" />
                </div>
                <div>
                  <CardTitle class="text-base">{{ source.name }}</CardTitle>
                  <CardDescription class="mt-1">{{ source.batch }}</CardDescription>
                </div>
              </div>
              <Badge variant="info">batch</Badge>
            </div>
          </CardHeader>
          <CardContent class="grid gap-4 px-5">
            <p class="text-sm leading-6 text-muted-foreground">{{ source.description }}</p>
            <div class="flex flex-wrap gap-2">
              <Badge v-for="event in source.events" :key="event" variant="outline">
                {{ event }}
              </Badge>
            </div>
            <div class="batch-stream" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          </CardContent>
        </Card>
      </div>

      <div class="rounded-[1.75rem] border border-border bg-white p-4 soft-panel-shadow md:p-5">
        <div class="grid gap-3 md:grid-cols-4">
          <div
            v-for="(stage, index) in stages"
            :key="stage.title"
            :class="
              cn(
                'event-stage rounded-2xl border border-border bg-white p-4 transition-all',
                stageStatus(index) === 'running' && 'event-stage-active',
              )
            "
          >
            <div class="flex items-start justify-between gap-3">
              <div class="flex size-9 items-center justify-center rounded-lg border border-border bg-secondary">
                <component :is="stage.icon" class="size-4" aria-hidden="true" />
              </div>
              <Badge
                :variant="
                  stageStatus(index) === 'done'
                    ? 'success'
                    : stageStatus(index) === 'running'
                      ? 'warning'
                      : 'outline'
                "
              >
                {{ stageStatus(index) }}
              </Badge>
            </div>
            <h3 class="mt-4 text-sm font-semibold">{{ stage.title }}</h3>
            <p class="mt-2 min-h-12 text-xs leading-5 text-muted-foreground">
              {{ stage.description }}
            </p>
            <p class="mt-3 text-sm font-semibold">{{ stage.metric }}</p>
          </div>
        </div>

        <Separator class="my-5" />

        <div class="grid gap-4 md:grid-cols-[0.92fr_1.08fr]">
          <div class="rounded-2xl bg-muted p-4">
            <div class="flex items-center gap-3">
              <ChartNoAxesCombined class="size-5 text-sky-600" aria-hidden="true" />
              <div>
                <p class="text-sm font-semibold">Goal statistics</p>
                <p class="text-xs text-muted-foreground">Updated as workflow nodes finish.</p>
              </div>
            </div>
            <div class="mt-4 grid gap-3">
              <div
                v-for="item in stats"
                :key="item.label"
                class="rounded-xl border border-border bg-white p-3"
              >
                <div class="flex items-center justify-between gap-3">
                  <span class="text-xs text-muted-foreground">{{ item.label }}</span>
                  <span class="text-lg font-semibold">{{ item.value }}</span>
                </div>
                <p class="mt-1 text-xs text-muted-foreground">{{ item.detail }}</p>
              </div>
            </div>
          </div>

          <div class="rounded-2xl border border-border bg-white p-4">
            <p class="text-sm font-semibold">Generated communication chain</p>
            <div class="mt-4 grid gap-3">
              <div class="flex items-center justify-between rounded-xl bg-muted px-3 py-2">
                <span class="text-sm">purchase_completed</span>
                <Badge variant="success">goal reached</Badge>
              </div>
              <div class="flex items-center justify-between rounded-xl bg-muted px-3 py-2">
                <span class="text-sm">cart_abandoned</span>
                <Badge variant="warning">start recovery</Badge>
              </div>
              <div class="flex items-center justify-between rounded-xl bg-muted px-3 py-2">
                <span class="text-sm">install_without_signup</span>
                <Badge variant="info">nurture</Badge>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
