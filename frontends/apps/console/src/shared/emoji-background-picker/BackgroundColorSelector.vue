<script setup lang="ts">
import { computed } from "vue";

import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

import { DEFAULT_EMOJI_BACKGROUND } from "./constants";
import type { EmojiBackgroundPickerLabels } from "./types";
import { normalizeHexColor } from "./utils";

const props = defineProps<{
  modelValue: string;
  emoji: string;
  isValid: boolean;
  labels: EmojiBackgroundPickerLabels;
  backgroundPresets: string[];
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
}>();

const backgroundValue = computed({
  get: () => props.modelValue,
  set: (value: string | number) => emit("update:modelValue", String(value)),
});
const displayedBackground = computed(
  () => normalizeHexColor(props.modelValue) || DEFAULT_EMOJI_BACKGROUND,
);

function isSelectedBackground(background: string) {
  return (
    normalizeHexColor(props.modelValue).toUpperCase() ===
    background.toUpperCase()
  );
}
</script>

<template>
  <div class="border-b p-3">
    <div class="mb-2 flex items-center justify-between gap-3">
      <p class="text-xs font-semibold tracking-wide text-foreground uppercase">
        {{ labels.backgroundLabel }}
      </p>
      <span class="text-xs text-muted-foreground">
        {{ displayedBackground }}
      </span>
    </div>
    <div
      class="emoji-background-picker-scrollbar-hide flex gap-2 overflow-x-auto p-2"
    >
      <button
        v-for="backgroundPreset in backgroundPresets"
        :key="backgroundPreset"
        type="button"
        :class="
          cn(
            'flex size-8 shrink-0 items-center justify-center rounded-lg border transition focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
            isSelectedBackground(backgroundPreset) &&
              'ring-ring ring-2 ring-offset-2',
          )
        "
        :style="{ backgroundColor: backgroundPreset }"
        :aria-label="labels.useBackgroundLabel(backgroundPreset)"
        @click="backgroundValue = backgroundPreset"
      >
        <span class="text-lg leading-none">{{ emoji }}</span>
      </button>
    </div>

    <div class="mt-2 grid grid-cols-[2.5rem_minmax(0,1fr)] gap-2">
      <Input
        v-model="backgroundValue"
        :aria-label="labels.backgroundInputAriaLabel"
        class="h-9 p-1"
        type="color"
      />
      <Input
        v-model="backgroundValue"
        :aria-invalid="!isValid"
        class="h-9"
        :placeholder="DEFAULT_EMOJI_BACKGROUND"
      />
    </div>
    <p v-if="!isValid" class="mt-1 text-xs text-destructive">
      {{ labels.validationMessage }}
    </p>
  </div>
</template>

<style scoped>
.emoji-background-picker-scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.emoji-background-picker-scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>
