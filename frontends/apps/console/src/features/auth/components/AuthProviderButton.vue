<script setup lang="ts">
import type {HTMLAttributes} from "vue";

import {cn} from "@/lib/utils";

const props = withDefaults(
    defineProps<{
      provider: "google" | "microsoft";
      variant?: "dark" | "outline";
      disabled?: boolean;
      class?: HTMLAttributes["class"];
    }>(),
    {
      variant: "dark",
      disabled: false
    }
);

const providerLabel = {
  google: "G",
  microsoft: "M"
};

const providerClass = {
  google: "bg-[#4285f4]",
  microsoft: "bg-[#f25022]"
};
</script>

<template>
  <button
      type="button"
      :disabled="disabled"
      :class="cn(
      'inline-flex min-h-7 w-full items-center justify-center gap-2 rounded text-[0.72rem] font-semibold transition-colors',
      variant === 'dark'
        ? 'bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-100'
        : 'border border-neutral-200 bg-white text-neutral-900 hover:bg-neutral-50',
      props.class
    )"
  >
    <span
        :class="cn(
        'grid size-3.5 place-items-center rounded-[3px] text-[0.56rem] font-extrabold text-white',
        providerClass[provider]
      )"
        aria-hidden="true"
    >
      {{ providerLabel[provider] }}
    </span>
    <slot/>
  </button>
</template>
