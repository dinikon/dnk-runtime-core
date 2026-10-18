import { ref, watch } from "vue";
import { changeProductContent } from "./product-content-draft.ts";

export function useProductContentDraft(
  source: () => Record<string, string> | null | undefined,
  scope: () => string,
  dirty: () => boolean,
  save: (values: Record<string, string>) => void,
  reset: () => number = () => 0,
) {
  const values = ref<Record<string, string>>({});
  watch(
    [scope, source, reset],
    ([nextScope, next, token], previous) => {
      if (nextScope !== previous?.[0] || token !== previous?.[2] || !dirty())
        values.value = { ...next };
    },
    { immediate: true },
  );
  function change(code: "title" | "body", value: string | undefined): void {
    values.value = changeProductContent(values.value, code, value);
    save({ ...values.value });
  }
  return { values, change };
}
