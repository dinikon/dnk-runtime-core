import {
  DEFAULT_EMOJI,
  DEFAULT_EMOJI_BACKGROUND,
  HEX_COLOR_PATTERN,
} from "./constants";

export function normalizeHexColor(value: string) {
  return value.trim();
}

export function isHexColor(value: string) {
  return HEX_COLOR_PATTERN.test(normalizeHexColor(value));
}

export function getPreviewBackground(
  value: string,
  fallback = DEFAULT_EMOJI_BACKGROUND,
) {
  return isHexColor(value) ? normalizeHexColor(value) : fallback;
}

export function getPreviewEmoji(value: string, fallback = DEFAULT_EMOJI) {
  return value.trim() || fallback;
}
