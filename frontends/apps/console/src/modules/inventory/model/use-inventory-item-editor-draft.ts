import { computed, reactive, watch, type Ref, type ComputedRef } from "vue";
import { InventoryItemEditorDraft } from "./inventory-item-editor-draft.ts";
import type { InventoryItemDetails } from "./inventory-item-settings.types";
import type {
  InventoryItemChanges,
  InventoryItemEditValues,
} from "./inventory-item-editor.types";
export interface InventoryItemEditorDraftState {
  values: ComputedRef<InventoryItemEditValues | null>;
  changes: ComputedRef<InventoryItemChanges>;
  dirty: ComputedRef<boolean>;
  change(value: InventoryItemEditValues): void;
  addBarcode(): void;
  reset(): void;
  clear(): void;
  rebase(result: InventoryItemDetails): void;
  acknowledge(
    sent: InventoryItemEditValues,
    result: InventoryItemDetails,
  ): void;
}
export function useInventoryItemEditorDraft(
  source: () => InventoryItemDetails | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): InventoryItemEditorDraftState {
  const draft = reactive(new InventoryItemEditorDraft());
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
    changes: computed(() => draft.changes),
    dirty: computed(() => draft.dirty),
    change: (value) => draft.change(value),
    addBarcode: () => draft.addBarcode(),
    reset: () => {
      const value = source();
      if (value) draft.reset(value);
    },
    clear: () => draft.clear(),
    rebase: (result) => draft.rebase(result),
    acknowledge: (sent, result) => draft.acknowledge(sent, result),
  };
}
