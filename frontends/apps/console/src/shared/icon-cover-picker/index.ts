export { default as IconCoverPicker } from "./components/IconCoverPicker.vue";
export {
  DEFAULT_ICON_COVER_BACKGROUND,
  HEX_COLOR_PATTERN,
  ICON_COVER_BACKGROUND_PRESETS,
} from "./model/constants";
export type {
  IconCoverPickerLabels,
  IconCoverPickerProps,
} from "./model/types";
export { isHexColor, normalizeHexColor } from "./model/utils";
