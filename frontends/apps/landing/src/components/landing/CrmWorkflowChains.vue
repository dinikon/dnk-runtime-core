<script setup lang="ts">
import type { Component } from "vue";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  BellRing,
  GitBranch,
  Mail,
  MessageSquareText,
  Pause,
  Play,
  Repeat2,
  Smartphone,
  Target,
  TimerReset,
  UsersRound,
} from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import WorkflowNodeCard from "./WorkflowNodeCard.vue";

type NodeStatus = "queued" | "running" | "done";
type NodeAccent = "teal" | "amber" | "blue" | "graphite";

type WorkflowStep = {
  title: string;
  label: string;
  metric: string;
  channel: string;
  icon: Component;
  accent: NodeAccent;
};

type WorkflowChain = {
  id: string;
  title: string;
  description: string;
  audience: string;
  goal: string;
  steps: WorkflowStep[];
};

const chains: WorkflowChain[] = [
  {
    id: "lead-nurture",
    title: "Lead nurture",
    description:
      "Turn a product event into a measured CRM conversation across email, push, and delayed follow-up.",
    audience: "New leads with intent score above 64",
    goal: "Book demo",
    steps: [
      {
        title: "Capture",
        label: "Pricing signal",
        metric: "0.18s",
        channel: "event",
        icon: BellRing,
        accent: "teal",
      },
      {
        title: "Segment",
        label: "Profile lookup",
        metric: "12k",
        channel: "data",
        icon: UsersRound,
        accent: "blue",
      },
      {
        title: "Email",
        label: "Offer email",
        metric: "98.2%",
        channel: "email",
        icon: Mail,
        accent: "teal",
      },
      {
        title: "Wait",
        label: "Wait 24h",
        metric: "24h",
        channel: "delay",
        icon: TimerReset,
        accent: "graphite",
      },
      {
        title: "Goal",
        label: "Demo booked",
        metric: "31.8%",
        channel: "goal",
        icon: Target,
        accent: "amber",
      },
    ],
  },
  {
    id: "payment-recovery",
    title: "Payment recovery",
    description:
      "Coordinate retries with provider fallbacks and support handoff without losing tenant execution context.",
    audience: "Invoices with failed authorization",
    goal: "Recover payment",
    steps: [
      {
        title: "Trigger",
        label: "Payment failed",
        metric: "live",
        channel: "billing",
        icon: BellRing,
        accent: "amber",
      },
      {
        title: "Branch",
        label: "Reason split",
        metric: "4 paths",
        channel: "logic",
        icon: GitBranch,
        accent: "blue",
      },
      {
        title: "SMS",
        label: "Retry link",
        metric: "sent",
        channel: "sms",
        icon: Smartphone,
        accent: "teal",
      },
      {
        title: "Retry",
        label: "Fallback",
        metric: "2 tries",
        channel: "delivery",
        icon: Repeat2,
        accent: "graphite",
      },
      {
        title: "Goal",
        label: "Invoice paid",
        metric: "44.1%",
        channel: "goal",
        icon: Target,
        accent: "amber",
      },
    ],
  },
  {
    id: "winback",
    title: "Winback",
    description:
      "Use recent product telemetry to choose channel, cadence, and final stop conditions for dormant customers.",
    audience: "Customers inactive for 21 days",
    goal: "Return session",
    steps: [
      {
        title: "Detect",
        label: "Dormant",
        metric: "21d",
        channel: "event",
        icon: BellRing,
        accent: "blue",
      },
      {
        title: "Branch",
        label: "Consent",
        metric: "7 rules",
        channel: "logic",
        icon: GitBranch,
        accent: "amber",
      },
      {
        title: "Push",
        label: "Push alert",
        metric: "queued",
        channel: "push",
        icon: Smartphone,
        accent: "teal",
      },
      {
        title: "Message",
        label: "Chat fallback",
        metric: "open",
        channel: "chat",
        icon: MessageSquareText,
        accent: "teal",
      },
      {
        title: "Goal",
        label: "Session started",
        metric: "18.6%",
        channel: "goal",
        icon: Target,
        accent: "amber",
      },
    ],
  },
];

const selectedChainId = ref(chains[0].id);
const activeStepIndex = ref(0);
const isRunning = ref(true);
let timer: number | undefined;

const activeChain = computed(
  () => chains.find((chain) => chain.id === selectedChainId.value) ?? chains[0],
);

const activeStep = computed(
  () => activeChain.value.steps[activeStepIndex.value] ?? activeChain.value.steps[0],
);

const progressPercent = computed(() =>
  Math.round(((activeStepIndex.value + 1) / activeChain.value.steps.length) * 100),
);

const executionLog = computed(() => [
  `${activeStep.value.channel} checkpoint saved`,
  `${activeChain.value.goal.toLowerCase()} attribution window updated`,
  "Tenant outbox and statistics stay in one trace",
]);

function statusFor(index: number): NodeStatus {
  if (index < activeStepIndex.value) {
    return "done";
  }

  if (index === activeStepIndex.value) {
    return "running";
  }

  return "queued";
}

function selectChain(id: string) {
  selectedChainId.value = id;
}

function toggleRunning() {
  isRunning.value = !isRunning.value;
}

function nextStep() {
  activeStepIndex.value = (activeStepIndex.value + 1) % activeChain.value.steps.length;
}

watch(selectedChainId, () => {
  activeStepIndex.value = 0;
  isRunning.value = true;
});

onMounted(() => {
  timer = window.setInterval(() => {
    if (isRunning.value) {
      nextStep();
    }
  }, 2400);
});

onBeforeUnmount(() => {
  if (timer !== undefined) {
    window.clearInterval(timer);
  }
});
</script>

<template>
  <section id="crm-workflows" class="mx-auto w-full max-w-7xl px-5 py-16 md:px-8">
    <div class="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <h2 class="text-balance text-3xl font-semibold leading-tight sm:text-4xl">
          CRM workflow chains that execute, branch, and measure.
        </h2>
        <p class="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">
          Build communication journeys from product events, tenant data, provider
          delivery, wait windows, and goal attribution instead of one-off
          campaigns.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <Badge variant="success">Live execution</Badge>
        <Button type="button" variant="outline" size="sm" class="bg-white" @click="toggleRunning">
          <Pause v-if="isRunning" data-icon="inline-start" aria-hidden="true" />
          <Play v-else data-icon="inline-start" aria-hidden="true" />
          {{ isRunning ? "Pause" : "Run" }}
        </Button>
      </div>
    </div>

    <div class="grid gap-5 lg:grid-cols-[0.72fr_1.28fr]">
      <div class="flex flex-col gap-3">
        <Button
          v-for="chain in chains"
          :key="chain.id"
          :data-testid="`chain-${chain.id}`"
          type="button"
          :variant="selectedChainId === chain.id ? 'default' : 'outline'"
          class="h-auto w-full justify-start whitespace-normal rounded-xl px-4 py-3 text-left"
          @click="selectChain(chain.id)"
        >
          <span class="grid gap-1">
            <span class="text-sm font-semibold">{{ chain.title }}</span>
            <span class="text-xs opacity-80">{{ chain.goal }} / {{ chain.audience }}</span>
          </span>
        </Button>

        <Card class="rounded-2xl py-5" data-testid="crm-chain-inspector">
          <CardHeader class="px-5">
            <CardTitle class="text-base">Chain inspector</CardTitle>
            <CardDescription class="leading-6">
              {{ activeChain.description }}
            </CardDescription>
          </CardHeader>
          <CardContent class="grid gap-3 px-5">
            <div class="flex items-center justify-between rounded-lg bg-muted px-3 py-2 text-sm">
              <span class="text-muted-foreground">Audience</span>
              <span class="font-medium">{{ activeChain.audience }}</span>
            </div>
            <div class="flex items-center justify-between rounded-lg bg-muted px-3 py-2 text-sm">
              <span class="text-muted-foreground">Current step</span>
              <span class="font-medium">{{ activeStep.title }}</span>
            </div>
            <div class="flex items-center justify-between rounded-lg bg-muted px-3 py-2 text-sm">
              <span class="text-muted-foreground">Goal progress</span>
              <Badge variant="warning">{{ progressPercent }}%</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <div class="workflow-grid rounded-[1.75rem] border border-border bg-white p-4 soft-panel-shadow md:p-5">
        <div class="mb-5 flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <p class="text-sm font-semibold text-muted-foreground">Executing chain</p>
            <h3 class="mt-1 text-2xl font-semibold">{{ activeChain.title }}</h3>
          </div>
          <Badge variant="info">{{ activeChain.goal }}</Badge>
        </div>

        <div class="workflow-chain-progress" aria-hidden="true">
          <span :style="{ width: `${progressPercent}%` }" />
        </div>

        <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <WorkflowNodeCard
            v-for="(step, index) in activeChain.steps"
            :key="`${activeChain.id}-${step.title}`"
            v-bind="step"
            :status="statusFor(index)"
          />
        </div>

        <div class="mt-5 grid gap-3 md:grid-cols-[1fr_0.9fr]">
          <div class="rounded-2xl border border-border bg-white/90 p-4">
            <div class="flex items-center justify-between gap-3">
              <p class="text-sm font-semibold">Active execution</p>
              <Badge variant="outline">{{ activeStep.channel }}</Badge>
            </div>
            <div class="mt-4 flex items-center gap-3 rounded-xl bg-muted p-3">
              <span class="execution-pulse" aria-hidden="true" />
              <div>
                <p class="text-sm font-semibold">{{ activeStep.title }}</p>
                <p class="text-xs text-muted-foreground">{{ activeStep.label }}</p>
              </div>
            </div>
          </div>

          <div class="rounded-2xl border border-border bg-white/90 p-4">
            <p class="text-sm font-semibold">Runtime log</p>
            <div class="mt-4 grid gap-2">
              <div
                v-for="entry in executionLog"
                :key="entry"
                class="flex items-start gap-2 text-xs leading-5 text-muted-foreground"
              >
                <span class="mt-2 size-1.5 shrink-0 rounded-full bg-teal-500" />
                <span>{{ entry }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
