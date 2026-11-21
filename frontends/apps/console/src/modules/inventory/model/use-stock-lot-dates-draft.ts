import { computed, reactive, watch, type Ref, type ComputedRef } from "vue";
import { StockLotDatesDraft } from "./stock-lot-dates-draft.ts";
import type {
  StockLotDatesValues,
  StockLotDatesChanges,
} from "./stock-lot.types";
export interface StockLotDatesDraftState {
  values: ComputedRef<StockLotDatesValues | null>;
  dirty: ComputedRef<boolean>;
  changes: ComputedRef<StockLotDatesChanges>;
  change(value: StockLotDatesValues): void;
  reset(): void;
  clear(): void;
  rebase(value: StockLotDatesValues): void;
  acknowledge(sent: StockLotDatesValues, result: StockLotDatesValues): void;
}
export function useStockLotDatesDraft(
  source: () => StockLotDatesValues | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): StockLotDatesDraftState {
  const draft = reactive(new StockLotDatesDraft());
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
    clear: () => draft.clear(),
    rebase: (value) => draft.rebase(value),
    acknowledge: (sent, result) => draft.acknowledge(sent, result),
  };
}
