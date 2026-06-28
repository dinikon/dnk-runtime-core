<script setup lang="ts">
import type { HTMLAttributes } from "vue";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const props = defineProps<{
  icon: string;
  background: string;
  ariaLabel: string;
  invalid?: boolean;
  disabled?: boolean;
  triggerClass?: HTMLAttributes["class"];
  iconClass?: HTMLAttributes["class"];
}>();
</script>

<template>
  <Button
    type="button"
    variant="outline"
    :disabled="disabled"
    :class="
      cn(
        'size-14 rounded-2xl p-1 shadow-xs transition hover:bg-background',
        invalid && 'border-destructive ring-destructive/20 ring-2',
        props.triggerClass,
      )
    "
    :aria-label="ariaLabel"
  >
    <span
      :class="
        cn(
          'flex size-full items-center justify-center rounded-xl text-3xl shadow-inner',
          props.iconClass,
        )
      "
      :style="{ backgroundColor: background }"
      aria-hidden="true"
    >
      {{ icon }}
    </span>
  </Button>
</template>
