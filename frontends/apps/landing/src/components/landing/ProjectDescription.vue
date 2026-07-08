<script setup lang="ts">
import { DatabaseZap, MessagesSquare, Network } from "@lucide/vue";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const capabilities = [
  {
    title: "Tenant runtime",
    description:
      "Resolve every request by host, keep execution scoped to one tenant, and move work between runtime servers without changing product code.",
    icon: Network,
  },
  {
    title: "Schema-aware data",
    description:
      "Use runtime metadata and physical tenant schemas to keep records, CRM objects, and workflow payloads aligned.",
    icon: DatabaseZap,
  },
  {
    title: "Communication orchestration",
    description:
      "Connect provider catalogs, templates, delivery attempts, and workflow actions through one observable execution path.",
    icon: MessagesSquare,
  },
];
</script>

<template>
  <section id="project" class="mx-auto w-full max-w-7xl px-5 py-20 md:px-8">
    <div class="grid gap-10 lg:grid-cols-[0.82fr_1.18fr] lg:items-start">
      <div>
        <h2 class="text-balance text-3xl font-semibold leading-tight sm:text-4xl">
          A runtime core for products that need tenant control.
        </h2>
        <p class="mt-5 max-w-xl text-base leading-7 text-muted-foreground">
          DNK separates product execution from orchestration concerns. The
          runtime handles tenant-local work; the control plane can own DNS,
          provisioning, placement, and migration as the platform grows.
        </p>
      </div>

      <div class="grid gap-4 md:grid-cols-3">
        <Card
          v-for="capability in capabilities"
          :key="capability.title"
          class="rounded-2xl py-5"
        >
          <CardHeader class="px-5">
            <div class="flex size-10 items-center justify-center rounded-lg border border-border bg-secondary">
              <component :is="capability.icon" class="size-4" aria-hidden="true" />
            </div>
            <CardTitle class="pt-3 text-base">{{ capability.title }}</CardTitle>
            <CardDescription class="leading-6">
              {{ capability.description }}
            </CardDescription>
          </CardHeader>
          <CardContent class="px-5">
            <Separator />
          </CardContent>
        </Card>
      </div>
    </div>
  </section>
</template>
