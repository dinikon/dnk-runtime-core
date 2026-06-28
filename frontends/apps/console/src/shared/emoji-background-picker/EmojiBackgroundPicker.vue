<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";

import BackgroundColorSelector from "./BackgroundColorSelector.vue";
import {
  DEFAULT_EMOJI_BACKGROUND_PICKER_LABELS,
  EMOJI_BACKGROUND_PRESETS,
} from "./constants";
import EmojiMartPanel from "./EmojiMartPanel.vue";
import EmojiPickerActions from "./EmojiPickerActions.vue";
import EmojiPickerHeader from "./EmojiPickerHeader.vue";
import EmojiPickerTrigger from "./EmojiPickerTrigger.vue";
import type {
  EmojiBackgroundPickerChange,
  EmojiBackgroundPickerLabels,
  EmojiBackgroundPickerProps,
} from "./types";
import {
  getPreviewBackground,
  getPreviewEmoji,
  isHexColor,
  normalizeHexColor,
} from "./utils";

const props = defineProps<EmojiBackgroundPickerProps>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
  (event: "update:background", value: string): void;
  (event: "change", value: EmojiBackgroundPickerChange): void;
}>();

const isOpen = ref(false);
const draftEmoji = ref(props.modelValue);
const draftBackground = ref(props.background);

const labels = computed<EmojiBackgroundPickerLabels>(() => ({
  ...DEFAULT_EMOJI_BACKGROUND_PICKER_LABELS,
  ...props.labels,
  title:
    props.title ??
    props.labels?.title ??
    DEFAULT_EMOJI_BACKGROUND_PICKER_LABELS.title,
  description:
    props.description ??
    props.labels?.description ??
    DEFAULT_EMOJI_BACKGROUND_PICKER_LABELS.description,
  useBackgroundLabel:
    props.labels?.useBackgroundLabel ??
    DEFAULT_EMOJI_BACKGROUND_PICKER_LABELS.useBackgroundLabel,
}));
const backgroundPresets = computed(
  () => props.backgroundPresets ?? EMOJI_BACKGROUND_PRESETS,
);
const hasValidDraftBackground = computed(() =>
  isHexColor(draftBackground.value),
);
const previewBackground = computed(() =>
  getPreviewBackground(draftBackground.value),
);
const previewEmoji = computed(() => getPreviewEmoji(draftEmoji.value));

function resetDraft() {
  draftEmoji.value = props.modelValue;
  draftBackground.value = props.background;
}

function selectEmoji(emoji: string) {
  draftEmoji.value = emoji;
}

function cancelSelection() {
  resetDraft();
  isOpen.value = false;
}

function applySelection() {
  if (!hasValidDraftBackground.value) {
    return;
  }

  const change = {
    emoji: draftEmoji.value,
    background: normalizeHexColor(draftBackground.value),
  };

  emit("update:modelValue", change.emoji);
  emit("update:background", change.background);
  emit("change", change);
  isOpen.value = false;
}

watch(isOpen, (open) => {
  if (open) {
    resetDraft();
  }
});

watch(
  () => props.modelValue,
  (value) => {
    if (!isOpen.value) {
      draftEmoji.value = value;
    }
  },
);

watch(
  () => props.background,
  (value) => {
    if (!isOpen.value) {
      draftBackground.value = value;
    }
  },
);
</script>

<template>
  <Dialog v-model:open="isOpen">
    <DialogTrigger as-child>
      <EmojiPickerTrigger
        :emoji="getPreviewEmoji(modelValue)"
        :background="getPreviewBackground(background)"
        :invalid="invalid"
        :disabled="disabled"
        :trigger-class="triggerClass"
        :emoji-class="emojiClass"
        :label="labels.triggerAriaLabel"
      />
    </DialogTrigger>
    <DialogContent
      :show-close-button="false"
      class="flex h-[min(38rem,calc(100dvh-1rem))] w-[min(23.25rem,calc(100vw-1rem))] max-w-none flex-col gap-0 overflow-hidden rounded-2xl p-0"
    >
      <div class="flex min-h-0 flex-1 flex-col">
        <EmojiPickerHeader
          :emoji="previewEmoji"
          :background="previewBackground"
          :title="labels.title"
          :description="labels.description"
        />

        <div class="min-h-0 flex-1 border-b bg-background">
          <EmojiMartPanel :open="isOpen" @select="selectEmoji" />
        </div>

        <BackgroundColorSelector
          v-model="draftBackground"
          :emoji="previewEmoji"
          :is-valid="hasValidDraftBackground"
          :labels="labels"
          :background-presets="backgroundPresets"
        />

        <EmojiPickerActions
          :cancel-label="labels.cancel"
          :confirm-label="labels.confirm"
          :apply-disabled="!hasValidDraftBackground"
          @cancel="cancelSelection"
          @apply="applySelection"
        />
      </div>
    </DialogContent>
  </Dialog>
</template>
