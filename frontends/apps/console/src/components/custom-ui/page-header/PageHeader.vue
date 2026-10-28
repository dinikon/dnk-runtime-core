<script setup lang="ts">
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

withDefaults(
  defineProps<{
    title: string;
    description?: string;
    compact?: boolean;
  }>(),
  { compact: false },
);
</script>

<template>
  <header
    class="@container/page-header flex w-full min-w-0 flex-col gap-6"
    data-slot="page-header"
  >
    <slot name="before" />
    <div
      :class="
        cn(
          'flex min-w-0 gap-6',
          compact
            ? 'flex-row flex-wrap items-center justify-between'
            : 'flex-col @2xl/page-header:flex-row @2xl/page-header:items-center @2xl/page-header:justify-between',
        )
      "
    >
      <div
        class="flex min-w-0 flex-1 flex-col gap-4 @2xl/page-header:flex-row @2xl/page-header:items-center"
      >
        <slot name="leading" />
        <div class="flex min-w-0 flex-col gap-2">
          <h1
            :class="
              cn(
                'font-semibold tracking-tight',
                compact
                  ? 'text-xl @2xl/page-header:text-2xl'
                  : 'text-2xl @2xl/page-header:text-3xl',
              )
            "
          >
            {{ title }}
          </h1>
          <p
            v-if="description"
            class="text-sm text-muted-foreground @2xl/page-header:text-base"
          >
            {{ description }}
          </p>
        </div>
      </div>
      <slot name="actions" />
    </div>
    <slot name="after" />
    <Separator v-if="!$slots.after" />
  </header>
</template>
