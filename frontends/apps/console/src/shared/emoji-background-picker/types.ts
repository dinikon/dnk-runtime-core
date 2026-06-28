import type { HTMLAttributes } from "vue";

export interface EmojiBackgroundPickerLabels {
  triggerAriaLabel: string;
  title: string;
  description: string;
  backgroundLabel: string;
  backgroundInputAriaLabel: string;
  validationMessage: string;
  cancel: string;
  confirm: string;
  useBackgroundLabel: (color: string) => string;
}

export interface EmojiBackgroundPickerProps {
  modelValue: string;
  background: string;
  title?: string;
  description?: string;
  invalid?: boolean;
  disabled?: boolean;
  triggerClass?: HTMLAttributes["class"];
  emojiClass?: HTMLAttributes["class"];
  labels?: Partial<EmojiBackgroundPickerLabels>;
  backgroundPresets?: string[];
}

export interface EmojiBackgroundPickerChange {
  emoji: string;
  background: string;
}

export interface EmojiMartSelection {
  native?: string;
}
