<script setup lang="ts">
import type { Component } from "vue";
import { CheckCircle2, Clock3, Loader2 } from "@lucide/vue";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type NodeStatus = "queued" | "running" | "done";

const props = defineProps<{
  title: string;
  label: string;
  metric: string;
  status: NodeStatus;
  icon: Component;
  accent: "teal" | "amber" | "blue" | "graphite";
  compact?: boolean;
}>();

const statusLabels: Record<NodeStatus, string> = {
  queued: "Queued",
  running: "Running",
  done: "Done",
};

const accentClasses = {
  teal: "border-teal-200 bg-teal-50 text-teal-700",
  amber: "border-amber-200 bg-amber-50 text-amber-800",
  blue: "border-sky-200 bg-sky-50 text-sky-700",
  graphite: "border-neutral-200 bg-neutral-50 text-neutral-700",
};

const statusClasses: Record<NodeStatus, string> = {
  queued: "border-neutral-200 bg-white text-muted-foreground",
  running: "border-amber-200 bg-amber-50 text-amber-800",
  done: "border-teal-200 bg-teal-50 text-teal-700",
};
</script>

<template>
  <article
    :class="
      cn(
        'workflow-node-glow rounded-xl border bg-white/95 p-4 transition-all duration-300',
        status === 'running' && 'border-amber-300 shadow-amber-100',
        status === 'done' && 'border-teal-200',
        status === 'queued' && 'border-border',
        compact && 'p-3',
      )
    "
  >
    <div v-if="compact" class="flex items-start gap-3">
      <div class="flex min-w-0 items-center gap-3">
        <div
          :class="
            cn(
              'flex size-9 shrink-0 items-center justify-center rounded-lg border',
              accentClasses[accent],
              compact && 'size-8',
            )
          "
        >
          <component :is="icon" class="size-4" aria-hidden="true" />
        </div>
        <div class="min-w-0">
          <h3
            :class="
              cn(
                'text-sm font-semibold leading-5 text-foreground',
                compact && 'text-[13px]',
              )
            "
          >
            {{ title }}
          </h3>
          <p
            :class="
              cn(
                'text-xs leading-4 text-muted-foreground',
                compact && 'text-[11px]',
              )
            "
          >
            {{ label }}
          </p>
        </div>
      </div>
    </div>

    <div v-else>
      <div class="flex min-w-0 items-center gap-3">
        <div
          :class="
            cn(
              'flex size-9 shrink-0 items-center justify-center rounded-lg border',
              accentClasses[accent],
            )
          "
        >
          <component :is="icon" class="size-4" aria-hidden="true" />
        </div>
        <div class="min-w-0">
          <h3 class="text-sm font-semibold leading-5 text-foreground">
            {{ title }}
          </h3>
          <p class="text-xs leading-4 text-muted-foreground">
            {{ label }}
          </p>
        </div>
      </div>

      <div class="mt-4 flex items-center justify-between gap-3">
        <Badge variant="outline" :class="cn('gap-1', statusClasses[status])">
          <Loader2
            v-if="status === 'running'"
            class="size-3 animate-spin"
            aria-hidden="true"
          />
          <CheckCircle2
            v-else-if="status === 'done'"
            class="size-3"
            aria-hidden="true"
          />
          <Clock3 v-else class="size-3" aria-hidden="true" />
          {{ statusLabels[status] }}
        </Badge>
        <span class="shrink-0 text-xs font-medium text-muted-foreground">
          {{ metric }}
        </span>
      </div>
    </div>

    <div
      :class="
        cn(
          'flex items-center justify-between gap-3',
          compact ? 'mt-4' : 'mt-3',
        )
      "
    >
      <div class="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-muted">
        <div
          :class="
            cn(
              'h-full rounded-full transition-all duration-500',
              status === 'done' && 'w-full bg-teal-500',
              status === 'running' && 'w-2/3 bg-amber-500',
              status === 'queued' && 'w-1/5 bg-neutral-300',
            )
          "
        />
      </div>
      <span
        v-if="compact"
        class="shrink-0 text-xs font-medium text-muted-foreground"
      >
        {{ metric }}
      </span>
    </div>
  </article>
</template>
