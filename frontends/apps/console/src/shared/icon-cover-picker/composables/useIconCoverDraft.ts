import { computed, ref } from "vue";

import { DEFAULT_ICON_COVER_BACKGROUND } from "../model/constants";
import { isHexColor, normalizeHexColor } from "../model/utils";

export function useIconCoverDraft(
  initialIcon: string,
  initialBackground: string,
  fallbackBackground = DEFAULT_ICON_COVER_BACKGROUND,
) {
  const draftIcon = ref(initialIcon);
  const draftBackground = ref(initialBackground);

  const hasValidDraftBackground = computed(() =>
    isHexColor(draftBackground.value),
  );
  const previewBackground = computed(() =>
    hasValidDraftBackground.value
      ? normalizeHexColor(draftBackground.value)
      : fallbackBackground,
  );

  function resetDraft(icon: string, background: string) {
    draftIcon.value = icon;
    draftBackground.value = background;
  }

  function commitDraft() {
    if (!hasValidDraftBackground.value) {
      return null;
    }

    return {
      icon: draftIcon.value,
      background: normalizeHexColor(draftBackground.value),
    };
  }

  return {
    draftIcon,
    draftBackground,
    hasValidDraftBackground,
    previewBackground,
    resetDraft,
    commitDraft,
  };
}
