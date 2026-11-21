import { computed, reactive, watch, type Ref, type ComputedRef } from "vue";
import type {
  StockLocationEditValues,
  StockLocationChanges,
} from "./stock-location.types";
import { StockLocationDraft } from "./stock-location-draft.ts";
export interface StockLocationDraftState {
  values: ComputedRef<StockLocationEditValues | null>;
  dirty: ComputedRef<boolean>;
  changes: ComputedRef<StockLocationChanges>;
  change(value: StockLocationEditValues): void;
  reset(): void;
  acknowledge(
    sent: StockLocationEditValues,
    result: StockLocationEditValues,
  ): void;
}
export function useStockLocationDraft(
  source: () => StockLocationEditValues | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): StockLocationDraftState {
  const draft = reactive(new StockLocationDraft());
  watch(identity, () => draft.clear(), { flush: "sync" });
  watch(
    () => [source(), pending.value] as const,
    ([value, saving]) => {
      if (value && !saving) draft.receive(value);
    },
    { immediate: true, flush: "sync" },
  );
  return {
    values: computed(() => draft.values),
    dirty: computed(() => draft.dirty),
    changes: computed(() => draft.changes),
    change: (value) => draft.change(value),
    reset: () => {
      const value = source();
      if (value) draft.reset(value);
    },
    acknowledge: (sent, result) => draft.acknowledge(sent, result),
  };
}
