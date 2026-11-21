import { computed, reactive, watch, type Ref, type ComputedRef } from "vue";
import type {
  PackagingTypeEditValues,
  PackagingTypeChanges,
} from "./packaging-type.types";
import { PackagingTypeDraft } from "./packaging-type-draft.ts";
export interface PackagingTypeDraftState {
  values: ComputedRef<PackagingTypeEditValues | null>;
  dirty: ComputedRef<boolean>;
  changes: ComputedRef<PackagingTypeChanges>;
  change(value: PackagingTypeEditValues): void;
  reset(): void;
  acknowledge(
    sent: PackagingTypeEditValues,
    result: PackagingTypeEditValues,
  ): void;
}
export function usePackagingTypeDraft(
  source: () => PackagingTypeEditValues | undefined,
  identity: Ref<string>,
  pending: Ref<boolean>,
): PackagingTypeDraftState {
  const draft = reactive(new PackagingTypeDraft());
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
