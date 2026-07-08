<script setup lang="ts">
import { DialogDescription, DialogTitle } from "@/components/ui/dialog";

defineProps<{
  emoji: string;
  background: string;
  title: string;
  description: string;
}>();
</script>

<template>
  <div class="border-b px-3 py-2.5">
    <div class="flex items-center gap-3">
      <div
        class="flex size-10 shrink-0 items-center justify-center rounded-xl text-2xl shadow-inner"
        :style="{ backgroundColor: background }"
        aria-hidden="true"
      >
        {{ emoji }}
      </div>
      <div class="min-w-0">
        <DialogTitle class="text-base font-semibold">
          {{ title }}
        </DialogTitle>
        <DialogDescription class="sr-only">
          {{ description }}
        </DialogDescription>
      </div>
    </div>
  </div>
</template>
