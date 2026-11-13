import { computed, reactive, watch, type Ref, type ComputedRef } from "vue";
import type {
  ItemPackagingValues,
  ItemPackagingChanges,
} from "./item-packaging.types";
import { ItemPackagingDraft } from "./item-packaging-draft.ts";
export interface ItemPackagingDraftState {
  values: ComputedRef<ItemPackagingValues | null>;
  dirty: ComputedRef<boolean>;
  changes: ComputedRef<ItemPackagingChanges>;
  change(value: ItemPackagingValues): void;
  reset(): void;
  acknowledge(
    sent: ItemPackagingValues,
    result: ItemPackagingValues,
  ): void;
}
export function useItemPackagingDraft(
  source: () => ItemPackagingValues | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): ItemPackagingDraftState {
  const draft = reactive(new ItemPackagingDraft());
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
