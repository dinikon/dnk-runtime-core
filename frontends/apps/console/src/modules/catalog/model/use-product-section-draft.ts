import { ref, watch, type Ref } from "vue";
import { clone } from "./clone";

/** Сброс подтверждённого раздела не заменяет более новый ввод. */
export function useProductSectionDraft<T>(
  source: () => T,
  reset: () => number,
  save: (value: T) => void,
) {
  const value = ref(clone(source())) as Ref<T>;
  let dirty = false;
  function restore(): void {
    value.value = clone(source());
    dirty = false;
  }
  watch(reset, restore);
  watch(source, () => {
    if (!dirty) restore();
  });
  function change(next: T): void {
    dirty = true;
    value.value = next;
    save(clone(next));
  }
  return { value, change };
}
