<script setup lang="ts">
import type { HTMLAttributes } from "vue";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const props = withDefaults(
  defineProps<{
    provider: "google" | "microsoft";
    variant?: "dark" | "outline";
    disabled?: boolean;
    class?: HTMLAttributes["class"];
  }>(),
  {
    variant: "dark",
    disabled: false,
  },
);

const providerLabel = {
  google: "G",
  microsoft: "M",
};

const providerClass = {
  google: "bg-[#4285f4]",
  microsoft: "bg-[#f25022]",
};
</script>

<template>
  <Button
    type="button"
    class="w-full"
    :variant="variant === 'outline' ? 'outline' : 'default'"
    :disabled="disabled"
    :class="props.class"
  >
    <span
      :class="
        cn(
          'grid size-4 place-items-center rounded-[3px] text-[0.6rem] font-extrabold text-white',
          providerClass[provider],
        )
      "
      aria-hidden="true"
    >
      {{ providerLabel[provider] }}
    </span>
    <slot />
  </Button>
</template>
