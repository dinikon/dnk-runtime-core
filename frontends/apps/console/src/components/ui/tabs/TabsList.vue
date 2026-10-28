<script setup lang="ts">
import type { TabsListProps } from "reka-ui";
import type { HTMLAttributes } from "vue";
import { reactiveOmit } from "@vueuse/core";
import { TabsList } from "reka-ui";
import { cn } from "@/lib/utils";

const props = withDefaults(
  defineProps<
    TabsListProps & {
      class?: HTMLAttributes["class"];
      variant?: "default" | "line";
    }
  >(),
  { variant: "default" },
);

const delegatedProps = reactiveOmit(props, "class", "variant");
</script>

<template>
  <TabsList
    data-slot="tabs-list"
    v-bind="delegatedProps"
    :class="
      cn(
        props.variant === 'line'
          ? 'text-muted-foreground flex h-auto w-max min-w-full items-center justify-start gap-1 border-b p-0'
          : 'bg-muted text-muted-foreground inline-flex h-9 w-fit items-center justify-center rounded-lg p-[3px]',
        props.class,
      )
    "
  >
    <slot />
  </TabsList>
</template>
