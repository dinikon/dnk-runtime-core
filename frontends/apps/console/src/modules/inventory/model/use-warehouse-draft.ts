import { computed, reactive, watch, type Ref, type ComputedRef } from "vue";
import type { WarehouseEditValues, WarehouseChanges } from "./warehouse.types";
import { WarehouseDraft } from "./warehouse-draft.ts";
export interface WarehouseDraftState {
  values: ComputedRef<WarehouseEditValues | null>;
  dirty: ComputedRef<boolean>;
  changes: ComputedRef<WarehouseChanges>;
  change(value: WarehouseEditValues): void;
  reset(): void;
  acknowledge(sent: WarehouseEditValues, result: WarehouseEditValues): void;
}
export function useWarehouseDraft(
  source: () => WarehouseEditValues | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): WarehouseDraftState {
  const draft = reactive(new WarehouseDraft());
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
