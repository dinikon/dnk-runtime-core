<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import type { EmojiMartData } from "@emoji-mart/data";
import emojiData from "@emoji-mart/data/sets/15/native.json";
import { init, Picker } from "emoji-mart";

const emit = defineEmits<{
  (event: "select", value: string): void;
}>();

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

const emojiPickerHost = ref<HTMLElement | null>(null);
let emojiPickerElement: HTMLElement | null = null;

function selectEmoji(emoji: EmojiMartSelection) {
  if (emoji.native) {
    emit("select", emoji.native);
  }
}

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

  picker.classList.add("icon-cover-emoji-mart-picker");
  emojiPickerHost.value.appendChild(picker);
  emojiPickerElement = picker;
}

onMounted(async () => {
  await nextTick();
  mountEmojiMartPicker();
});

onBeforeUnmount(unmountEmojiMartPicker);
</script>

<template>
  <div ref="emojiPickerHost" class="h-full w-full" />
</template>

<style>
.icon-cover-emoji-mart-picker {
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
</style>
