import { HEX_COLOR_PATTERN } from "./constants";

export function normalizeHexColor(value: string) {
  return value.trim();
}

export function isHexColor(value: string) {
  return HEX_COLOR_PATTERN.test(normalizeHexColor(value));
}
