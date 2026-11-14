import { computed, reactive, watch, type Ref, type ComputedRef } from "vue";
import type { SourceValues, SourceChanges } from "./supplier-source.types";
import { SourceDraft } from "./source-draft";
export interface SourceDraftState {
  values: ComputedRef<SourceValues | null>;
  dirty: ComputedRef<boolean>;
  changes: ComputedRef<SourceChanges>;
  change(value: SourceValues): void;
  reset(): void;
  acknowledge(sent: SourceValues, result: SourceValues): void;
}
export function useSourceDraft(
  source: () => SourceValues | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): SourceDraftState {
  const draft = reactive(new SourceDraft());
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
