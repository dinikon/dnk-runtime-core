<script setup lang="ts">
import { computed, ref } from "vue";

import { useEmojiMartPicker } from "./useEmojiMartPicker";

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  (event: "select", value: string): void;
}>();

const emojiPickerHost = ref<HTMLElement | null>(null);
const isOpen = computed(() => props.open);

useEmojiMartPicker(emojiPickerHost, isOpen, (emoji) => emit("select", emoji));
</script>

<template>
  <div ref="emojiPickerHost" class="h-full w-full" />
</template>

<style>
.emoji-background-picker-mart {
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
