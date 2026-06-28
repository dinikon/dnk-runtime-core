<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import { useIconCoverDraft } from "../composables/useIconCoverDraft";
import {
  DEFAULT_ICON_COVER_PICKER_LABELS,
  ICON_COVER_BACKGROUND_PRESETS,
} from "../model/constants";
import type {
  IconCoverPickerLabels,
  IconCoverPickerProps,
} from "../model/types";
import CoverColorPicker from "./CoverColorPicker.vue";
import EmojiMartPanel from "./EmojiMartPanel.vue";
import IconPreviewButton from "./IconPreviewButton.vue";

const props = defineProps<IconCoverPickerProps>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
  (event: "update:background", value: string): void;
}>();

const isOpen = ref(false);
const {
  draftIcon,
  draftBackground,
  hasValidDraftBackground,
  previewBackground,
  resetDraft,
  commitDraft,
} = useIconCoverDraft(props.modelValue, props.background);

const labels = computed<IconCoverPickerLabels>(() => ({
  ...DEFAULT_ICON_COVER_PICKER_LABELS,
  ...props.labels,
  useBackgroundLabel:
    props.labels?.useBackgroundLabel ??
    DEFAULT_ICON_COVER_PICKER_LABELS.useBackgroundLabel,
}));
const backgroundPresets = computed(
  () => props.backgroundPresets ?? ICON_COVER_BACKGROUND_PRESETS,
);

function selectEmoji(emoji: string) {
  draftIcon.value = emoji;
}

function cancelSelection() {
  resetDraft(props.modelValue, props.background);
  isOpen.value = false;
}

function applySelection() {
  const draft = commitDraft();

  if (!draft) {
    return;
  }

  emit("update:modelValue", draft.icon);
  emit("update:background", draft.background);
  isOpen.value = false;
}

watch(isOpen, (open) => {
  if (open) {
    resetDraft(props.modelValue, props.background);
  }
});

watch(
  () => props.modelValue,
  (value) => {
    if (!isOpen.value) {
      draftIcon.value = value;
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
      <IconPreviewButton
        :icon="modelValue"
        :background="previewBackground"
        :invalid="invalid"
        :disabled="disabled"
        :trigger-class="triggerClass"
        :icon-class="iconClass"
        :aria-label="labels.triggerAriaLabel"
      />
    </DialogTrigger>
    <DialogContent
      :show-close-button="false"
      class="flex h-[min(38rem,calc(100dvh-1rem))] w-[min(23.25rem,calc(100vw-1rem))] max-w-none flex-col gap-0 overflow-hidden rounded-2xl p-0"
    >
      <div class="flex min-h-0 flex-1 flex-col">
        <div class="border-b px-3 py-2.5">
          <div class="flex items-center gap-3">
            <div
              class="flex size-10 shrink-0 items-center justify-center rounded-xl text-2xl shadow-inner"
              :style="{ backgroundColor: previewBackground }"
              aria-hidden="true"
            >
              {{ draftIcon }}
            </div>
            <div class="min-w-0">
              <DialogTitle class="text-base font-semibold">
                {{ labels.title }}
              </DialogTitle>
              <DialogDescription class="sr-only">
                {{ labels.description }}
              </DialogDescription>
            </div>
          </div>
        </div>

        <div class="min-h-0 flex-1 border-b bg-background">
          <EmojiMartPanel @select="selectEmoji" />
        </div>

        <CoverColorPicker
          v-model="draftBackground"
          :icon="draftIcon"
          :is-valid="hasValidDraftBackground"
          :labels="labels"
          :background-presets="backgroundPresets"
        />

        <div class="grid grid-cols-2 gap-2 p-3">
          <Button type="button" variant="outline" @click="cancelSelection">
            {{ labels.cancel }}
          </Button>
          <Button
            type="button"
            :disabled="!hasValidDraftBackground"
            @click="applySelection"
          >
            {{ labels.confirm }}
          </Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>
