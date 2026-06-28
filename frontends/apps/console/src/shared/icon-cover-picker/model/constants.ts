import type { IconCoverPickerLabels } from "./types";

export const DEFAULT_ICON_COVER_BACKGROUND = "#FDEAD7";

export const HEX_COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/;

export const ICON_COVER_BACKGROUND_PRESETS = [
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

export const DEFAULT_ICON_COVER_PICKER_LABELS: IconCoverPickerLabels = {
  triggerAriaLabel: "Choose icon and cover color",
  title: "Icon and cover",
  description: "Choose an emoji icon and cover background color.",
  backgroundLabel: "Background",
  backgroundInputAriaLabel: "Choose icon cover background color",
  validationMessage: `Use a hex color like ${DEFAULT_ICON_COVER_BACKGROUND}.`,
  cancel: "Cancel",
  confirm: "OK",
  useBackgroundLabel: (color) => `Use ${color}`,
};
