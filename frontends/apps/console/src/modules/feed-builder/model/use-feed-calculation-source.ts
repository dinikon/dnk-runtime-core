import { ref, watch, type Ref } from "vue";
import type { CatalogPriceChoice } from "./feed-calculation.types";
export interface FeedCalculationSource {
  search: Ref<string>;
  offset: Ref<number>;
  variantOffset: Ref<number>;
  root: Ref<CatalogPriceChoice | null>;
  variant: Ref<CatalogPriceChoice | null>;
  reset(): void;
}
export function useFeedCalculationSource(): FeedCalculationSource {
  const search = ref(""),
    offset = ref(0),
    variantOffset = ref(0),
    root = ref<CatalogPriceChoice | null>(null),
    variant = ref<CatalogPriceChoice | null>(null);
  watch(search, () => {
    offset.value = 0;
  });
  watch(
    () => root.value?.id,
    () => {
      variant.value = null;
      variantOffset.value = 0;
    },
    { flush: "sync" },
  );
  function reset(): void {
    root.value = null;
    variant.value = null;
    search.value = "";
    offset.value = 0;
    variantOffset.value = 0;
  }
  return { search, offset, variantOffset, root, variant, reset };
}
