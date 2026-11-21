import { computed, reactive, watch, type Ref, type ComputedRef } from "vue";
import { StockSerialDraft } from "./stock-serial-draft.ts";
import type {
  StockSerialValues,
  StockSerialChanges,
} from "./stock-serial.types";
export interface StockSerialDraftState {
  values: ComputedRef<StockSerialValues | null>;
  dirty: ComputedRef<boolean>;
  changes: ComputedRef<StockSerialChanges>;
  change(value: StockSerialValues): void;
  reset(): void;
  clear(): void;
  rebase(value: StockSerialValues): void;
  acknowledge(sent: StockSerialValues, result: StockSerialValues): void;
}
export function useStockSerialDraft(
  source: () => StockSerialValues | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): StockSerialDraftState {
  const draft = reactive(new StockSerialDraft());
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
