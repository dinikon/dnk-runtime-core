<script setup lang="ts">
import type { HTMLAttributes } from "vue";
import type { BadgeVariants } from ".";
import { badgeVariants } from ".";
import { cn } from "@/lib/utils";

const props = defineProps<{
  variant?: BadgeVariants["variant"];
  class?: HTMLAttributes["class"];
}>();
</script>

<template>
  <span
    data-slot="badge"
    :class="cn(badgeVariants({ variant: props.variant }), props.class)"
  >
    <slot />
  </span>
</template>
