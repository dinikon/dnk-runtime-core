<script setup lang="ts">
import { ArrowRight, ChartNoAxesCombined, ShieldCheck } from "@lucide/vue";
import { Button } from "@/components/ui/button";
import WorkflowMap from "./WorkflowMap.vue";
</script>

<template>
  <section class="mx-auto grid min-h-[calc(100svh-8rem)] w-full max-w-7xl items-center gap-10 px-5 pb-10 pt-8 md:px-8 lg:grid-cols-[0.88fr_1.12fr] lg:gap-12 lg:pt-12">
    <div class="max-w-2xl">
      <h1 class="text-balance text-5xl font-semibold leading-[1.02] text-foreground sm:text-6xl lg:text-[4.6rem]">
        Runtime for tenant workflows
      </h1>
      <p class="mt-6 max-w-xl text-pretty text-lg leading-8 text-muted-foreground">
        DNK helps teams design, run, and observe workflows that stay aware of
        tenant boundaries, schema metadata, communication providers, and runtime
        data.
      </p>

      <div class="mt-8 flex flex-col gap-3 sm:flex-row">
        <Button as="a" href="#workflow" size="lg" class="h-12">
          View workflow
          <ArrowRight data-icon="inline-end" aria-hidden="true" />
        </Button>
        <Button
          as="a"
          href="#project"
          variant="outline"
          size="lg"
          class="h-12 bg-white"
        >
          Explore platform
        </Button>
      </div>

      <dl class="mt-10 grid max-w-lg grid-cols-2 gap-4">
        <div class="rounded-xl border border-border bg-white p-4">
          <dt class="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <ShieldCheck class="size-4 text-teal-600" aria-hidden="true" />
            Tenant-aware
          </dt>
          <dd class="mt-2 text-2xl font-semibold">Isolated runtime</dd>
        </div>
        <div class="rounded-xl border border-border bg-white p-4">
          <dt class="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <ChartNoAxesCombined class="size-4 text-sky-600" aria-hidden="true" />
            Observable
          </dt>
          <dd class="mt-2 text-2xl font-semibold">Live execution</dd>
        </div>
      </dl>
    </div>

    <WorkflowMap />
  </section>
</template>
