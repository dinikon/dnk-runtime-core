import { nextTick, onBeforeUnmount, onMounted, type Ref, watch } from "vue";
import type { EmojiMartData } from "@emoji-mart/data";
import emojiData from "@emoji-mart/data/sets/15/native.json";
import { init, Picker } from "emoji-mart";

import { EMOJI_MART_CATEGORIES } from "./constants";
import type { EmojiMartSelection } from "./types";

const emojiMartData = emojiData as EmojiMartData;

let emojiMartInitPromise: Promise<void> | null = null;

function initEmojiMart() {
  emojiMartInitPromise ??= init({ data: emojiMartData });

  return emojiMartInitPromise;
}

export function useEmojiMartPicker(
  host: Ref<HTMLElement | null>,
  open: Ref<boolean>,
  onSelect: (emoji: string) => void,
) {
  let pickerElement: HTMLElement | null = null;

  function selectEmoji(emoji: EmojiMartSelection) {
    if (emoji.native) {
      onSelect(emoji.native);
    }
  }

  function unmount() {
    pickerElement?.remove();
    pickerElement = null;
  }

  async function mount() {
    if (!open.value || !host.value) {
      return;
    }

    await initEmojiMart();

    if (!open.value || !host.value) {
      return;
    }

    unmount();

    const picker = new Picker({
      data: emojiMartData,
      categories: EMOJI_MART_CATEGORIES,
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

    picker.classList.add("emoji-background-picker-mart");
    host.value.appendChild(picker);
    pickerElement = picker;
  }

  onMounted(async () => {
    await nextTick();
    await mount();
  });

  watch(open, async (isOpen) => {
    if (!isOpen) {
      unmount();
      return;
    }

    await nextTick();
    await mount();
  });

  onBeforeUnmount(unmount);

  return {
    mount,
  };
}
