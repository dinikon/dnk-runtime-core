import { ref, watch, type Ref } from "vue";
import {
  togglePublicationChoice,
  mergePublicationChoices,
  publicationReferenceKey,
} from "./feed-publication.selection";
import type { PublicationChoice } from "./feed-publication.types";
export function usePublicationSelection(): {
  selected: Ref<PublicationChoice[]>;
  search: Ref<string>;
  offset: Ref<number>;
  rootId: Ref<string>;
  variantOffset: Ref<number>;
  error: Ref<string>;
  toggle(value: PublicationChoice): void;
  merge(values: PublicationChoice[]): void;
  reset(): void;
  remove(value: PublicationChoice): void;
} {
  const selected = ref<PublicationChoice[]>([]),
    search = ref(""),
    offset = ref(0),
    rootId = ref(""),
    variantOffset = ref(0),
    error = ref("");
  watch(search, () => {
    offset.value = 0;
  });
  watch(rootId, () => {
    variantOffset.value = 0;
  });
  function toggle(value: PublicationChoice): void {
    try {
      selected.value = togglePublicationChoice(selected.value, value);
      error.value = "";
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Проверьте выбор.";
    }
  }
  function merge(values: PublicationChoice[]): void {
    try {
      selected.value = mergePublicationChoices(selected.value, values);
      error.value = "";
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Проверьте выбор.";
    }
  }
  function remove(value: PublicationChoice): void {
    selected.value = selected.value.filter(
      (v) => publicationReferenceKey(v) !== publicationReferenceKey(value),
    );
  }
  function reset(): void {
    selected.value = [];
    search.value = "";
    offset.value = 0;
    rootId.value = "";
    variantOffset.value = 0;
    error.value = "";
  }
  return {
    selected,
    search,
    offset,
    rootId,
    variantOffset,
    error,
    toggle,
    merge,
    reset,
    remove,
  };
}
