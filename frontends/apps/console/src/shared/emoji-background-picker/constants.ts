import type { EmojiBackgroundPickerLabels } from "./types";

export const DEFAULT_EMOJI_BACKGROUND = "#FDEAD7";

export const DEFAULT_EMOJI = "🚀";

export const HEX_COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/;

export const EMOJI_BACKGROUND_PRESETS = [
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
];

export const EMOJI_MART_CATEGORIES = [
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

export const DEFAULT_EMOJI_BACKGROUND_PICKER_LABELS: EmojiBackgroundPickerLabels =
  {
    triggerAriaLabel: "Choose emoji and background color",
    title: "Emoji and background",
    description: "Choose an emoji and background color.",
    backgroundLabel: "Background",
    backgroundInputAriaLabel: "Choose emoji background color",
    validationMessage: `Use a hex color like ${DEFAULT_EMOJI_BACKGROUND}.`,
    cancel: "Cancel",
    confirm: "OK",
    useBackgroundLabel: (color) => `Use ${color}`,
  };
