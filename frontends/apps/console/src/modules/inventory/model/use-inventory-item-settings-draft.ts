import { computed, reactive, watch, type ComputedRef, type Ref } from "vue";
import { InventorySettingsDraft } from "./inventory-item-settings-draft.ts";
import type { InventoryItemSettings } from "./inventory-item-settings.types";

export interface InventoryItemSettingsDraftState {
  values: ComputedRef<InventoryItemSettings | null>;
  dirty: ComputedRef<boolean>;
  change(value: InventoryItemSettings): void;
  reset(): void;
  acknowledge(sent: InventoryItemSettings, result: InventoryItemSettings): void;
}

export function useInventoryItemSettingsDraft(
  source: () => InventoryItemSettings | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): InventoryItemSettingsDraftState {
  const draft = reactive(new InventorySettingsDraft());
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
    change: (value) => draft.change(value),
    reset: () => {
      const value = source();
      if (value) draft.reset(value);
    },
    acknowledge: (sent, result) => draft.acknowledge(sent, result),
  };
}
