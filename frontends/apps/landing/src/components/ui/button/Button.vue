<script setup lang="ts">
import type { HTMLAttributes } from "vue";
import type { ButtonVariants } from ".";
import { buttonVariants } from ".";
import { cn } from "@/lib/utils";

const props = withDefaults(
  defineProps<{
    as?: string;
    variant?: ButtonVariants["variant"];
    size?: ButtonVariants["size"];
    class?: HTMLAttributes["class"];
  }>(),
  {
    as: "button",
  },
);
</script>

<template>
  <component
    :is="props.as"
    data-slot="button"
    :class="cn(buttonVariants({ variant: props.variant, size: props.size }), props.class)"
  >
    <slot />
  </component>
</template>
