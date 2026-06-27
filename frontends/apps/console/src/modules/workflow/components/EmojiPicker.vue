<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import type { EmojiMartData } from "@emoji-mart/data";
import type { HTMLAttributes } from "vue";
import emojiData from "@emoji-mart/data/sets/15/native.json";
import { init, Picker } from "emoji-mart";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const props = defineProps<{
  modelValue: string;
  background: string;
  invalid?: boolean;
  triggerClass?: HTMLAttributes["class"];
  iconClass?: HTMLAttributes["class"];
}>();

const emit = defineEmits<{
  (event: "update:modelValue", value: string): void;
  (event: "update:background", value: string): void;
}>();

const DEFAULT_BACKGROUND = "#FDEAD7";
const hexColorPattern = /^#[0-9A-Fa-f]{6}$/;
const backgroundPresets = [
  "#FDEAD7",
  "#DCFCE7",
  "#CFFAFE",
  "#DBEAFE",
  "#EDE9FE",
  "#FCE7F3",
  "#FEF3C7",
  "#E2E8F0",
  "#FECACA",
  "#FED7AA",
  "#BBF7D0",
  "#BAE6FD",
  "#C7D2FE",
  "#DDD6FE",
  "#FBCFE8",
  "#D1D5DB",
  "#2563EB",
  "#16A34A",
  "#EA580C",
  "#7C3AED",
];
const emojiMartData = emojiData as EmojiMartData;
const emojiMartCategories = [
  "frequent",
  "people",
  "nature",
  "foods",
  "activity",
  "places",
  "objects",
  "symbols",
  "flags",
];

interface EmojiMartSelection {
  native?: string;
}

void init({ data: emojiMartData });

const isOpen = ref(false);
const draftEmoji = ref(props.modelValue);
const draftBackground = ref(props.background);
const emojiPickerHost = ref<HTMLElement | null>(null);
let emojiPickerElement: HTMLElement | null = null;

function selectEmoji(emoji: EmojiMartSelection) {
  if (emoji.native) {
    draftEmoji.value = emoji.native;
  }
}

const hasValidDraftBackground = computed(() =>
  hexColorPattern.test(draftBackground.value.trim()),
);
const previewBackground = computed(() =>
  hasValidDraftBackground.value
    ? draftBackground.value.trim()
    : DEFAULT_BACKGROUND,
);

function unmountEmojiMartPicker() {
  emojiPickerElement?.remove();
  emojiPickerElement = null;
}

function mountEmojiMartPicker() {
  if (!emojiPickerHost.value) {
    return;
  }

  unmountEmojiMartPicker();

  const picker = new Picker({
    data: emojiMartData,
    categories: emojiMartCategories,
    dynamicWidth: true,
    emojiButtonRadius: "0.5rem",
    emojiButtonSize: 34,
    emojiSize: 22,
    maxFrequentRows: 1,
    navPosition: "bottom",
    previewPosition: "none",
    searchPosition: "none",
    set: "native",
    skinTonePosition: "none",
    theme: "auto",
    onEmojiSelect: selectEmoji,
  }) as unknown as HTMLElement;

  picker.classList.add("workflow-emoji-mart-picker");
  emojiPickerHost.value.appendChild(picker);
  emojiPickerElement = picker;
}

async function openEmojiMartPicker() {
  await nextTick();
  mountEmojiMartPicker();
}

function cancelSelection() {
  draftEmoji.value = props.modelValue;
  draftBackground.value = props.background;
  isOpen.value = false;
}

function applySelection() {
  if (!hasValidDraftBackground.value) {
    return;
  }

  emit("update:modelValue", draftEmoji.value);
  emit("update:background", draftBackground.value.trim());
  isOpen.value = false;
}

watch(isOpen, (open) => {
  if (open) {
    draftEmoji.value = props.modelValue;
    draftBackground.value = props.background;
    void openEmojiMartPicker();
  } else {
    unmountEmojiMartPicker();
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

onBeforeUnmount(unmountEmojiMartPicker);
</script>

<template>
  <Dialog v-model:open="isOpen">
    <DialogTrigger as-child>
      <Button
        type="button"
        variant="outline"
        :class="
          cn(
            'size-14 rounded-2xl p-1 shadow-xs transition hover:bg-background',
            invalid && 'border-destructive ring-destructive/20 ring-2',
            props.triggerClass,
          )
        "
        aria-label="Choose workflow icon"
      >
        <span
          :class="
            cn(
              'flex size-full items-center justify-center rounded-xl text-3xl shadow-inner',
              props.iconClass,
            )
          "
          :style="{ backgroundColor: previewBackground }"
          aria-hidden="true"
        >
          {{ modelValue }}
        </span>
      </Button>
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
              {{ draftEmoji }}
            </div>
            <div class="min-w-0">
              <DialogTitle class="text-base font-semibold">
                Smile + background
              </DialogTitle>
              <DialogDescription class="sr-only">
                Choose an emoji and background color for the workflow.
              </DialogDescription>
            </div>
          </div>
        </div>

        <div class="min-h-0 flex-1 border-b bg-background">
          <div ref="emojiPickerHost" class="h-full w-full" />
        </div>

        <div class="border-b p-3">
          <div class="mb-2 flex items-center justify-between gap-3">
            <p
              class="text-xs font-semibold tracking-wide text-foreground uppercase"
            >
              Background
            </p>
            <span class="text-xs text-muted-foreground">
              {{ draftBackground.trim() || DEFAULT_BACKGROUND }}
            </span>
          </div>
          <div class="flex gap-2 overflow-x-auto p-2 scrollbar-hide">
            <button
              v-for="backgroundPreset in backgroundPresets"
              :key="backgroundPreset"
              type="button"
              :class="
                cn(
                  'flex size-8 shrink-0 items-center justify-center rounded-lg border transition focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
                  draftBackground.trim().toUpperCase() ===
                    backgroundPreset.toUpperCase() &&
                    'ring-ring ring-2 ring-offset-2',
                )
              "
              :style="{ backgroundColor: backgroundPreset }"
              :aria-label="`Use ${backgroundPreset}`"
              @click="draftBackground = backgroundPreset"
            >
              <span class="text-lg leading-none">{{ draftEmoji }}</span>
            </button>
          </div>

          <div class="mt-2 grid grid-cols-[2.5rem_minmax(0,1fr)] gap-2">
            <Input
              v-model="draftBackground"
              aria-label="Choose icon background color"
              class="h-9 p-1"
              type="color"
            />
            <Input
              v-model="draftBackground"
              :aria-invalid="!hasValidDraftBackground"
              class="h-9"
              placeholder="#FDEAD7"
            />
          </div>
          <p
            v-if="!hasValidDraftBackground"
            class="mt-1 text-xs text-destructive"
          >
            Use a hex color like #FDEAD7.
          </p>
        </div>

        <div class="grid grid-cols-2 gap-2 p-3">
          <Button type="button" variant="outline" @click="cancelSelection">
            Cancel
          </Button>
          <Button
            type="button"
            :disabled="!hasValidDraftBackground"
            @click="applySelection"
          >
            OK
          </Button>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>

<style>
.workflow-emoji-mart-picker {
  width: 100%;
  height: 100%;
  min-height: 17rem;
  border-radius: 0;
  box-shadow: none;
  --border-radius: 0;
  --font-family:
    Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --rgb-accent: 37, 99, 235;
  --shadow: none;
}

@utility scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}
</style>
