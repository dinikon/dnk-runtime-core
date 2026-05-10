<script setup lang="ts">
import type {HTMLAttributes} from "vue";

import {cn} from "@/lib/utils";

const props = defineProps<{
  class?: HTMLAttributes["class"];
}>();
</script>

<template>
  <div
      :class="cn(
      'grid w-full max-w-[304px] gap-2.5 rounded bg-white px-8 py-7 text-center text-neutral-900 shadow-sm',
      props.class
    )"
  >
    <slot/>
  </div>
</template>
