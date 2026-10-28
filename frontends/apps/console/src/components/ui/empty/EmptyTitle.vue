<script setup lang="ts">
import type { HTMLAttributes } from "vue";
import type { PrimitiveProps } from "reka-ui";
import { Primitive } from "reka-ui";
import { cn } from "@/lib/utils";

interface Props extends PrimitiveProps {
  class?: HTMLAttributes["class"];
  size?: "default" | "lg";
}

const props = withDefaults(defineProps<Props>(), {
  as: "div",
  size: "default",
});
</script>

<template>
  <Primitive
    :as="props.as"
    :as-child="props.asChild"
    data-slot="empty-title"
    :class="cn(
      'tracking-tight',
      props.size === 'lg' ? 'text-xl font-semibold' : 'text-lg font-medium',
      props.class,
    )"
  >
    <slot />
  </Primitive>
</template>
