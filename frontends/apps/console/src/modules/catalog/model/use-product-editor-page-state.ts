import { computed, type ComputedRef } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  productEditorGroup,
  productEditorTab,
  type ProductEditorTab,
} from "./product-editor-state.ts";
import type { EditorGroup } from "./product-editor-layout";

export function useProductEditorPageState(
  variable: () => boolean,
  variant = false,
): {
  tab: ComputedRef<ProductEditorTab>;
  initialGroup: ComputedRef<EditorGroup | undefined>;
  selectTab: (value: ProductEditorTab) => void;
} {
  const route = useRoute();
  const router = useRouter();
  const key = variant ? "variant_tab" : "tab";
  const tab = computed(() => productEditorTab(route.query[key], variable()));
  const initialGroup = computed(() => productEditorGroup(route.query[key]));
  function selectTab(value: ProductEditorTab): void {
    void router.replace({
      query: {
        ...route.query,
        [key]: value === "description" ? undefined : value,
        ...(!variant && value !== "variants"
          ? { variant: undefined, variant_tab: undefined }
          : {}),
      },
      hash: route.hash,
    });
  }
  return { tab, initialGroup, selectTab };
}
